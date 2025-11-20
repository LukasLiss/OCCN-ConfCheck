import os
import pm4py
import pandas as pd
from typing import Any, Dict, List
from datetime import datetime
from container_logistics_occn import occn_container_logistics, occn_container_logistics_small
from pm4py.algo.occn_evaluation.replay_fitness import algorithm as occn_replay_fitness
from p2p_occn import occn_p2p
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.util import process_executions

def ocel_on_occn_eval(occn, ocel, ocel_name):
    # Pre-filter OCEL for px extaction
    ocel = pm4py.filter_ocel_object_types_allowed_activities(
        ocel, activities_for_px_extraction(ocel_name)
    )
    # Derive process executions
    px_results = process_executions.apply(ocel, variant="connected_components")
    pxs = px_results["process_executions"]
    print(f"Derived {len(pxs)} process executions from OCEL.")
    # filter out activities not captured by the OCCN
    pxs_filtered = filter_pxs(pxs, ocel, activities_in_occn(ocel_name))

    # filter ocel in the same way
    ocel_filtered = pm4py.filter_ocel_object_types_allowed_activities(
        ocel, activities_in_occn(ocel_name)
    )
    
    ots = ocel.objects[constants.DEFAULT_OBJECT_TYPE].unique()
    print(f"OCEL has object types: {ots}")
    ots = ocel_filtered.objects[constants.DEFAULT_OBJECT_TYPE].unique()
    print(f"Filtered OCEL has object types: {ots}")
    
    events_removed = len(ocel.events) - len(ocel_filtered.events)
    print(f"Filtered OCEL has {len(ocel_filtered.events)} events (removed {events_removed}).")
    px_filtered_events = sum(len(px) for px in pxs_filtered)
    px_events_removed = sum(len(px) for px in pxs) - px_filtered_events
    print(f"Filtered process executions have {px_filtered_events} events (removed {px_events_removed}).")

    # replay filtered pxs on OCCN
    eval_results = occn_replay_fitness.apply(occn=occn, ocel=ocel_filtered, process_executions=pxs_filtered)
    print(f"Evaluation results: \n log_fitness: {eval_results['log_fitness']}, \n no_process_executions: {eval_results['no_process_executions']}")
    # log results
    _log_results(eval_results, ocel_name)

def activities_in_occn(ocel_name):
    """
    Activities per object type present in the respective OCCN.
    
    Parameters
    ----------------
    ocel_name
        Name of the OCEL
    
    Returns
    -----------------
    activity_dict
        Dictionary of object types to present activities, e.g.,
        {"order": ["Create Order"], "element": ["Create Order", "Create Delivery"]}
    """
    if ocel_name == "ContainerLogistics.json":
        return {
            "Customer Order": ["Register Customer Order", "Create Transport Document"],
            "Transport Document": [
                "Create Transport Document",
                "Book Vehicles",
                "Order Empty Containers",
                "Depart",
            ],
            "Handling Unit": [
                "Collect Goods",
                "Load Truck",
            ],
            "Container": [
                "Order Empty Containers",
                "Pick Up Empty Container",
                "Load Truck",
                "Depart",
            ],
        }
    elif ocel_name == "ContainerLogistics.json-small":
        return {
            "Handling Unit": [
                "Collect Goods",
                "Load Truck",
            ],
            "Container": [
                "Order Empty Containers",
                "Pick Up Empty Container",
                "Load Truck",
            ],
        }
    elif ocel_name == "ocel2-p2p.json":
        return {
            "purchase_requisition": [ 
                "Create Purchase Requisition",
                "Approve Purchase Requisition",
                "Delegate Purchase Requisition Approval",
                "Create Request for Quotation",
            ],
            "material": [
                "Create Purchase Requisition",
                "Approve Purchase Requisition",
                "Delegate Purchase Requisition Approval",
            ],
            "quotation": [
                "Create Request for Quotation",
                "Create Purchase Order",
                "Approve Purchase Order",
            ],
            "purchase_order": [
                "Create Purchase Order",
                "Approve Purchase Order",
                "Create Goods Receipt",
                "Execute Payment",
            ],
            "goods receipt": [
                "Create Goods Receipt",
                "Create Invoice Receipt",
                "Perform Two-Way Match",
                "Execute Payment",
            ],
            "invoice receipt": [
                "Create Invoice Receipt",
                "Perform Two-Way Match",
                "Execute Payment",
            ],
            "payment": [
                "Execute Payment",
            ],
        }
    else:
        raise ValueError(f"Unknown OCEL name: {ocel_name}")
    
def activities_for_px_extraction(ocel_name):
    """
    Activities per object type to be used for process execution extraction.
    
    Parameters
    ----------------
    ocel_name
        Name of the OCEL
    
    Returns
    -----------------
    activity_dict
        Dictionary of object types to allowed activities, e.g.,
        {"order": ["Create Order"], "element": ["Create Order", "Create Delivery"]}
    """
    if ocel_name == "ContainerLogistics.json":
        return {
            "Customer Order": ["Register Customer Order", "Create Transport Document"],
            "Transport Document": [
                "Create Transport Document",
                "Book Vehicles",
                "Order Empty Containers",
                "Depart",
                "Reschedule Container"
            ],
            "Handling Unit": [
                "Collect Goods",
                "Load Truck",
            ],
            "Container": [
                "Order Empty Containers",
                "Pick Up Empty Container",
                "Load Truck",
                "Drive to Terminal",
                "Weigh",
                "Place in Stock",
                "Bring to Loading Bay",
                "Load to Vehicle",
                "Reschedule Container",
                "Depart",
            ],
        }
    elif ocel_name == "ContainerLogistics.json-small":
        return {
            "Handling Unit": [
                "Collect Goods",
                "Load Truck",
            ],
            "Container": [
                "Order Empty Containers",
                "Pick Up Empty Container",
                "Load Truck",
                "Drive to Terminal",
                "Weigh",
                "Place in Stock",
                "Bring to Loading Bay",
                "Load to Vehicle",
                "Reschedule Container",
            ],
        }
    elif ocel_name == "ocel2-p2p.json":
        return activities_in_occn(ocel_name)
    else:
        raise ValueError(f"Unknown OCEL name: {ocel_name}")


def filter_pxs(pxs: List, ocel, activity_dict):
    """
    Filters process executions to keep only events with activities in the activity_dict.

    Parameters
    ----------------
    pxs
        List of process executions
    ocel
        Object-centric event log
    activity_dict
        Dictionary of object types to allowed activities, e.g.,
        {"order": ["Create Order"], "element": ["Create Order", "Create Delivery"]}

    Returns
    -----------------
    filtered_pxs
        List of filtered process executions
    """
    # Get all allowed activities
    allowed_activities = {
        activity for act_list in activity_dict.values() for activity in act_list
    }

    # Create a mapping from event IDs to activities
    try:
        event_to_activity_map = dict(
            zip(
                ocel.events[constants.DEFAULT_EVENT_ID],
                ocel.events[constants.DEFAULT_EVENT_ACTIVITY],
            )
        )
    except KeyError:
        raise ValueError(
            f"Error: Columns missing. Need '{constants.DEFAULT_EVENT_ID}' and '{constants.DEFAULT_EVENT_ACTIVITY}'."
        )

    filtered_pxs = []

    # Filter
    for px in pxs:
        filtered_px = [
            event_id
            for event_id in px
            if event_to_activity_map.get(event_id) in allowed_activities
        ]

        if filtered_px:
            filtered_pxs.append(filtered_px)

    return filtered_pxs

def _log_results(eval_results: Dict[str, Any], ocel_name: str, directory_path="evaluation/occn_cc_evaluation_results/data"):
    """
    Logs the timing results to .csv files.
    
    Parameters
    ----------------
    eval_results
        Evaluation results dictionary, expected to contain:
        - "time_per_event_count": List of (no_events, time, call_count, fitting) tuples
        - "time_per_object_count": List of (no_objects, time, call_count, fitting) tuples
    ocel_name
        Name of the OCEL
    directory_path
        Directory path to save the results
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created directory: {directory_path}")
    
    # Format: YYYY-MM-DD_HH-MM-SS
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    time_per_event_count = eval_results.get("time_per_event_count")
    
    if time_per_event_count:
        try:
            event_df = pd.DataFrame(time_per_event_count, columns=["no_events", "time", "call_count", "fitting"])
            
            event_filename = f"{now_str}_{ocel_name}_event.csv"
            event_filepath = os.path.join(directory_path, event_filename)
            
            event_df.to_csv(event_filepath, index=False)
            
            print(f"Successfully saved event results to: {os.path.abspath(event_filepath)}")
            
        except Exception as e:
            print(f"Error saving event results: {e}")
    else:
        print("No 'time_per_event_count' data found in results. Skipping event log.")

    time_per_object_count = eval_results.get("time_per_object_count")
    
    if time_per_object_count:
        try:
            object_df = pd.DataFrame(time_per_object_count, columns=["no_objects", "time", "call_count", "fitting"])
            
            object_filename = f"{now_str}_{ocel_name}_object.csv"
            object_filepath = os.path.join(directory_path, object_filename)
            
            object_df.to_csv(object_filepath, index=False)
            
            print(f"Successfully saved object results to: {os.path.abspath(object_filepath)}")
            
        except Exception as e:
            print(f"Error saving object results: {e}")
    else:
        print("No 'time_per_object_count' data found in results. Skipping object log.")


if __name__ == "__main__":
    ocel_name = "ContainerLogistics.json-small"
    # occn
    if ocel_name == "ContainerLogistics.json":
        occn = occn_container_logistics()
    elif ocel_name == "ContainerLogistics.json-small":
        occn = occn_container_logistics_small()
    elif ocel_name == "ocel2-p2p.json":
        occn = occn_p2p()
    else:
        raise ValueError(f"Unknown OCEL name: {ocel_name}") 
    # ocel
    ocel_path = os.path.join("evaluation", "event_logs", ocel_name)
    if ocel_name == "ContainerLogistics.json-small":
        ocel_path = os.path.join("evaluation", "event_logs", "ContainerLogistics.json")
    ocel = pm4py.read_ocel2(ocel_path)

    # eval
    ocel_on_occn_eval(occn, ocel, ocel_name)

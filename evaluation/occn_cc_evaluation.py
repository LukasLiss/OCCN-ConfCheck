import os
from typing import List
import pm4py
from container_logistics_occn import occn_container_logistics
from pm4py.algo.occn_evaluation.replay_fitness import algorithm as occn_replay_fitness
from p2p_occn import occn_p2p
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.util import process_executions


def ocel_on_occn_eval(occn, ocel, ocel_name):
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
    print(f"Evaluation results: {eval_results}")


def activities_in_occn(ocel_name):
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


if __name__ == "__main__":
    ocel_name = "ocel2-p2p.json"
    # occn
    if ocel_name == "ContainerLogistics.json":
        occn = occn_container_logistics()
    elif ocel_name == "ocel2-p2p.json":
        occn = occn_p2p()
    else:
        raise ValueError(f"Unknown OCEL name: {ocel_name}")
    # ocel
    ocel_path = os.path.join("evaluation", "event_logs", ocel_name)
    ocel = pm4py.read_ocel2(ocel_path)

    # eval
    ocel_on_occn_eval(occn, ocel, ocel_name)

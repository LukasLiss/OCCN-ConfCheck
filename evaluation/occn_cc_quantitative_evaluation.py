import os
import sys
import pm4py
import pandas as pd
from typing import Any, Dict, List
from datetime import datetime
from container_logistics_occn import (
    occn_container_logistics,
    occn_container_logistics_small,
)
from discover_occn import discover_occn_from_ocel
from pm4py.algo.occn_evaluation.replay_fitness import algorithm as occn_replay_fitness
from p2p_occn import occn_p2p
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.util import process_executions
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.ocel.util.log_ocel import from_traditional_log
from oc_flexible_heuristics_miner import occn_from_dump


def ocel_on_occn_eval(occn, ocel, ocel_name, filter_ocel_px=True):
    """
    Evaluates the fitness of an OCCN against an OCEL using process execution replay.
    Results are logged to CSV files.

    Parameters
    ----------------
    occn
        The object-centric causal net (OCCN) to evaluate.
    ocel
        The object-centric event log (OCEL) to evaluate against the OCCN.
    ocel_name
        Name of the OCEL file, used for logging and filtering.
    filter_ocel_px
        Whether to filter the OCEL and process executions based on activities present in the OCCN.
        If set to True, `activities_for_px_extraction` and `activities_in_occn` have to be defined for the given ocel_name.
    """
    # Pre-filter OCEL for px extaction
    if filter_ocel_px:
        ocel = pm4py.filter_ocel_object_types_allowed_activities(
            ocel, activities_for_px_extraction(ocel_name)
        )
    # Derive process executions
    px_results = process_executions.apply(ocel, variant="connected_components")
    pxs = px_results["process_executions"]
    print(f"Derived {len(pxs)} process executions from OCEL.")
    # filter out activities not captured by the OCCN
    if filter_ocel_px:
        pxs_filtered = filter_pxs(pxs, ocel, activities_in_occn(ocel_name))
        # filter ocel in the same way
        ocel_filtered = pm4py.filter_ocel_object_types_allowed_activities(
            ocel, activities_in_occn(ocel_name)
        )
    else:
        pxs_filtered = pxs
        ocel_filtered = ocel

    ots = ocel.objects[constants.DEFAULT_OBJECT_TYPE].unique()
    print(f"OCEL has object types: {ots}")
    ots = ocel_filtered.objects[constants.DEFAULT_OBJECT_TYPE].unique()
    print(f"Filtered OCEL has object types: {ots}")

    events_removed = len(ocel.events) - len(ocel_filtered.events)
    print(
        f"Filtered OCEL has {len(ocel_filtered.events)} events (removed {events_removed})."
    )
    px_filtered_events = sum(len(px) for px in pxs_filtered)
    px_events_removed = sum(len(px) for px in pxs) - px_filtered_events
    print(
        f"Filtered process executions have {px_filtered_events} events (removed {px_events_removed})."
    )

    # replay filtered pxs on OCCN
    eval_results = occn_replay_fitness.apply(
        occn=occn, ocel=ocel_filtered, process_executions=pxs_filtered
    )
    print(
        f"Evaluation results: \n log_fitness: {eval_results['log_fitness']}, \n no_process_executions: {eval_results['no_process_executions']}"
    )
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
                "Reschedule Container",
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


def _log_results(
    eval_results: Dict[str, Any],
    ocel_name: str,
    directory_path="evaluation/occn_cc_quantitative_evaluation_results/data",
):
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
            event_df = pd.DataFrame(
                time_per_event_count,
                columns=["no_events", "time", "call_count", "fitting"],
            )

            event_filename = f"{now_str}_{ocel_name}_event.csv"
            event_filepath = os.path.join(directory_path, event_filename)

            event_df.to_csv(event_filepath, index=False)

            print(
                f"Successfully saved event results to: {os.path.abspath(event_filepath)}"
            )

        except Exception as e:
            print(f"Error saving event results: {e}")
    else:
        print("No 'time_per_event_count' data found in results. Skipping event log.")

    time_per_object_count = eval_results.get("time_per_object_count")

    if time_per_object_count:
        try:
            object_df = pd.DataFrame(
                time_per_object_count,
                columns=["no_objects", "time", "call_count", "fitting"],
            )

            object_filename = f"{now_str}_{ocel_name}_object.csv"
            object_filepath = os.path.join(directory_path, object_filename)

            object_df.to_csv(object_filepath, index=False)

            print(
                f"Successfully saved object results to: {os.path.abspath(object_filepath)}"
            )

        except Exception as e:
            print(f"Error saving object results: {e}")
    else:
        print("No 'time_per_object_count' data found in results. Skipping object log.")


def ocel_from_traditional(ocel_name):
    """
    Imports an OCEL from a traditional event log in XES format.

    Parameters
    ----------------
    ocel_name
        Name of the OCEL file in XES format.

    Returns
    -----------------
    ocel
        The imported object-centric event log (OCEL).
    """
    log_path = os.path.join("evaluation", "event_logs", ocel_name)
    log = xes_importer.apply(log_path)
    ocel = from_traditional_log(log)
    print("Activities in imported OCEL:")
    print(ocel.events[constants.DEFAULT_EVENT_ACTIVITY].unique())
    return ocel


def occn_from_traditional(dumped_dir, relativeOccuranceThreshold):
    """
    Imports an OCCN from a dumped directory or mines it if the dump does not exist.

    Parameters
    ----------------
    dumped_dir
        Directory name where the dumped OCCN is stored.
    relativeOccuranceThreshold
        Threshold for relative occurrence to filter the OCCN after mining.

    Returns
    -----------------
    occn
        The loaded or mined object-centric causal network (OCCN).
    """
    dumped_path = os.path.join("evaluation", "discovered_occns", dumped_dir)
    if os.path.exists(dumped_path):
        occn = occn_from_dump(dumped_dir, relativeOccuranceThreshold, visualize=True)
        print(
            f"Loaded dumped OCCN from: {dumped_path} with relativeOccuranceThreshold={relativeOccuranceThreshold}"
        )
    else:
        print(
            f"Dumped OCCN path does not exist: {os.path.join('evaluation', 'discovered_occns', dumped_dir)}. Proceeding to mine OCCN."
        )
        occn = discover_occn_from_ocel(ocel, ocel_name, 0)
        print(f"Mined OCCN from traditional OCEL: {ocel_name}")
        print(
            "Please set the dumped_dir with the created dump and restart the evaluation."
        )
        sys.exit(1)
    return occn


if __name__ == "__main__":
    ocel_name = "Road_Traffic_Fine_Management_Process.xes"
    # occn
    filter_ocel_px = True
    if ocel_name == "ContainerLogistics.json":
        occn = occn_container_logistics()
    elif ocel_name == "ContainerLogistics.json-small":
        occn = occn_container_logistics_small()
    elif ocel_name == "ocel2-p2p.json":
        occn = occn_p2p()
    elif ocel_name == "BPI Challenge 2017.xes":  # traditional event log
        filter_ocel_px = False
        # Get log
        ocel = ocel_from_traditional(ocel_name)
        # Discover occn
        dumped_dir = "BPI Challenge 2017.xes_2025-11-26-09-08-27"
        relativeOccuranceThreshold = 0.2
        occn = occn_from_traditional(dumped_dir, relativeOccuranceThreshold)
    elif ocel_name == "BPI_Challenge_2012.xes":
        filter_ocel_px = False
        # Get log
        ocel = ocel_from_traditional(ocel_name)
        # Discover occn
        dumped_dir = "BPI_Challenge_2012.xes_2025-11-26-11-38-51"
        relativeOccuranceThreshold = 0
        occn = occn_from_traditional(dumped_dir, relativeOccuranceThreshold)
    elif ocel_name == "Road_Traffic_Fine_Management_Process.xes":
        filter_ocel_px = False
        # Get log
        ocel = ocel_from_traditional(ocel_name)
        # Discover occn
        dumped_dir = "Road_Traffic_Fine_Management_Process.xes_2025-11-26-12-28-28"
        relativeOccuranceThreshold = 0.2
        occn = occn_from_traditional(dumped_dir, relativeOccuranceThreshold)
    else:
        raise ValueError(f"Unknown OCEL name: {ocel_name}")
    # ocel
    if not ocel_name.endswith(".xes"):
        ocel_path = os.path.join("evaluation", "event_logs", ocel_name)
        if ocel_name == "ContainerLogistics.json-small":
            ocel_path = os.path.join(
                "evaluation", "event_logs", "ContainerLogistics.json"
            )
        ocel = pm4py.read_ocel2(ocel_path)

    # eval
    ocel_on_occn_eval(occn, ocel, ocel_name, filter_ocel_px)

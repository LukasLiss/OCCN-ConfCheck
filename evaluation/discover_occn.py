import os
from oc_flexible_heuristics_miner import discover_occn_fhm
import pm4py


def discover_occn():
    assert os.path.exists("evaluation/occn_visualization/src"), "evaluation/occn_visualization/src does not exist. Please copy the visualization dict from https://github.com/LukasLiss/OCCN-Miner to evaluation and rename it to 'occn_visualization'. Run npm install && npm run dev afterwards."
    
    file_name = "ocel2-p2p.json"
    ocel = discover_ocel(file_name)
    object_types = ocel.objects[ocel.object_type_column].unique().tolist()
    event_log, event_log_for_miner = _prepare_ocel_for_discovery(ocel)
    
    # Restrict to these object types
    #object_types = ["Customer Order", "Transport Document", "Container", "Handling Unit"]

    viz = True
    if os.path.exists("evaluation/occn_visualization/src") is False:
        viz = False
        print("evaluation/occn_visualization/src does not exist. Please copy the contents of the visualization directory from https://github.com/LukasLiss/OCCN-Miner into evaluation/occn_visualization. OCCN will not be visualized")
    discover_occn_fhm(event_log, event_log_for_miner, object_types, 0.5, file_name, viz)
    
def discover_occn_from_ocel(ocel, ocel_name, relativeOccurenceThreshold):
    object_types = ocel.objects[ocel.object_type_column].unique().tolist()
    event_log, event_log_for_miner = _prepare_ocel_for_discovery(ocel)
    
    viz = True
    if os.path.exists("evaluation/occn_visualization/src") is False:
        viz = False
        print("evaluation/occn_visualization/src does not exist. Please copy the contents of the visualization directory from https://github.com/LukasLiss/OCCN-Miner into evaluation/occn_visualization. OCCN will not be visualized")
    occn = discover_occn_fhm(event_log, event_log_for_miner, object_types, relativeOccurenceThreshold, ocel_name, viz)
    
    return occn


def discover_ocel(ocel_name):
    ocel_path = os.path.join("evaluation", "event_logs", ocel_name)
    ocel = pm4py.read_ocel2(ocel_path)

    return ocel


def _prepare_ocel_for_discovery(ocel):
    """
    Prepares the OCEL and returns two DataFrames:
    1. event_log: A log of unique events.
    2. event_log_for_miner: A flattened log of event-to-object relationships.
    """
    # Create event log
    event_log = ocel.events.rename(
        columns={
            ocel.event_id_column: "event_id",
            ocel.event_activity: "event_activity",
            ocel.event_timestamp: "event_timestamp",
        }
    )
    event_log = event_log[["event_id", "event_activity", "event_timestamp"]]

    # Create the event log for the miner

    # Get relations
    event_log_for_miner = ocel.relations.copy()

    # Rename cols to expected format
    event_log_for_miner = event_log_for_miner.rename(
        columns={
            ocel.event_activity: "event_activity",
            ocel.event_timestamp: "event_timestamp",
            ocel.object_id_column: "object",
            ocel.object_type_column: "object_type",
            ocel.event_id_column: "event_id",
        }
    )

    # Select only necessary columns
    required_columns = [
        "event_activity",
        "event_timestamp",
        "object",
        "object_type",
        "event_id",
    ]
    event_log_for_miner = event_log_for_miner[required_columns]

    # Drop rows with missing values and sort by timestamp
    event_log_for_miner = event_log_for_miner.dropna()
    event_log_for_miner = event_log_for_miner.sort_values(
        "event_timestamp", ignore_index=True
    )

    return event_log, event_log_for_miner


if __name__ == "__main__":
    discover_occn()

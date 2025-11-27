"""
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
"""

from collections import defaultdict
from enum import Enum
from typing import Any, Collection, Dict, List, Optional, Tuple

from tqdm import tqdm
from pm4py.util import exec_utils
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.oc_causal_net.semantics import OCCausalNetState, OCCausalNetSemantics
from pm4py.objects.ocel.util import process_executions as px_extraction
import time


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    PROCESS_EXECUTION_EXTRACTION = "process_execution_extraction"


def apply(
    occn: OCCausalNet,
    ocel: OCEL,
    process_executions: Optional[Collection] = None,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply process execution replay fitness evaluation.
    Assumes that start and end activities are capable of producing/consuming
    obligations for one object at a time.

    Parameters
    -----------
    occn
        Causal net
    ocel
        OCEL to evaluate
    process_executions
        Precomputed process executions. If None, process executions will be derived from the OCEL.
    parameters
        Parameters of the algorithm, including:
        - Parameters.EVENT_ID => the event identifier column
        - Parameters.EVENT_ACTIVITY => the event activity column
        - Parameters.EVENT_TIMESTAMP => the event timestamp column
        - Parameters.OBJECT_ID => the object identifier column
        - Parameters.OBJECT_TYPE => the object type column
        - Parameters.PROCESS_EXECUTION_EXTRACTION => the process execution extraction technique to use (default: 'connected_components')

    Returns
    -----------
    dictionary
        Results of the fitness evaluation:
            - 'log_fitness': overall fitness value (between 0 and 1)
            - 'no_process_executions': number of process executions derived from the log
    """
    if parameters is None:
        parameters = {}

    if process_executions:
        pxs = process_executions
    else:
        process_execution_extraction = exec_utils.get_param_value(
            Parameters.PROCESS_EXECUTION_EXTRACTION,
            parameters,
            "connected_components",
        )

        # Derive process executions
        px_results = px_extraction.apply(
            ocel, variant=process_execution_extraction, parameters=parameters
        )
        pxs = px_results["process_executions"]

    start_time = time.time()

    print("Building lookup maps for preprocessing...")
    start_setup_time = time.time()

    lookup_maps = _build_lookup_maps(ocel, parameters)

    end_setup_time = time.time()
    print(
        f"Lookup maps built in: {end_setup_time - start_setup_time:.4f} seconds."
    ) 

    end_time = time.time()
    print(
        f"Pre-build lookup maps time for {len(pxs)} process executions: {end_time - start_time:.4f} seconds."
    )  
    print(f"Starting fitness computation for {len(pxs)} process executions...")
    start_time = time.time()
    time_per_event_count = []
    time_per_object_count = []

    # Compute fitness
    total = 0
    fitting = 0

    for px in tqdm(pxs, desc="replay, completed px ::"):
        run_stats = {"calls": 0} 
        fitting_px = False
        px_start_time = time.time()

        # Preprocess px
        px_processed = _preprocess_single_px(px, *lookup_maps)

        # Check fitting
        if process_execution_fitting(occn, px_processed, stats=run_stats):
            fitting += 1
            fitting_px = True

        total += 1

        px_end_time = time.time()
        px_time = px_end_time - px_start_time 
        px_event_count = len(px) # Do not count START/End events
        px_object_count = len(set([x for _, ot_to_obj in px_processed for _, objs in ot_to_obj for x in objs]))
        call_count = run_stats["calls"]
        time_per_event_count.append((px_event_count, px_time, call_count, fitting_px))
        time_per_object_count.append((px_object_count, px_time, call_count, fitting_px))

    log_fitness = fitting / total if total > 0 else 0.0

    end_time = time.time()
    print(
        f"Fitness computation time for {len(pxs)} process executions: {end_time - start_time:.4f} seconds."
    )  

    return {
        "log_fitness": log_fitness,
        "no_process_executions": len(pxs),
        "time_per_event_count": time_per_event_count,
        "time_per_object_count": time_per_object_count, 
    }


def _preprocess_single_px(
    process_execution: Collection[Any],
    event_map: Dict,
    object_to_type_map: Dict,
    event_to_objs_map: Dict,
) -> List[Tuple]:
    """
    Preprocesses a process execution using the pre-built lookup maps.

    Parameters
    -----------
    process_execution
        A process execution, where a px is a collection of events ids
    event_map
        mapping from event ID to (timestamp, activity)
    object_to_type_map
        mapping from object ID to object type
    event_to_objs_map
        mapping from event ID to set of object IDs

    Returns
    -----------
    list
        Preprocessed process execution.
        A list of tuples of form (activity, object_type to object_ids mapping) where
        object_type to object_ids mapping is represented as a frozenset
        of (object_type, frozenset(object_ids)) pairs
    """
    px = list(process_execution)

    # order by timestamp
    px.sort(key=lambda event_id: event_map.get(event_id, (None, None))[0])

    px_new = []
    px_objects = defaultdict(set)

    # add activity id & objects involved
    for e in px:
        event_data = event_map.get(e, None)
        if event_data is None:
            print(f"[WARNING] Event id {e} not found in OCEL events.")
            continue

        activity = event_data[1]
        objs = event_to_objs_map.get(e, set())

        obj_by_type = defaultdict(list)
        for o in objs:
            obj_type = object_to_type_map.get(o)
            if obj_type:
                obj_by_type[obj_type].append(o)
            else:
                print(f"[WARNING] Object id {o} not found in OCEL objects.")

        for ot, o_list in obj_by_type.items():
            px_objects[ot].update(o_list)

        px_new.append(
            (activity, frozenset((k, frozenset(v)) for k, v in obj_by_type.items()))
        )

    # start and end activities per object
    start_events = []
    end_events = []
    for ot in px_objects:
        for o in px_objects[ot]:
            start_events.append((f"START_{ot}", frozenset({(ot, frozenset({o}))})))
            end_events.append((f"END_{ot}", frozenset({(ot, frozenset({o}))})))

    return start_events + px_new + end_events


def _build_lookup_maps(
    ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None
) -> Tuple:
    """
    Builds all necessary lookup maps for preprocessing.

    Parameters
    -----------
    ocel
        Object-centric event log
    parameters
        Parameters of the algorithm

    Returns
    -----------
    tuple
        A tuple containing:
            - event_map: mapping from event ID to (timestamp, activity)
            - object_to_type_map: mapping from object ID to object type
            - event_to_objs_map: mapping from event ID to set of object IDs
    """
    event_timestamp_key = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, constants.DEFAULT_EVENT_TIMESTAMP
    )
    object_id_key = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, constants.DEFAULT_OBJECT_ID
    )
    event_id_key = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, constants.DEFAULT_EVENT_ID
    )
    object_type_key = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, constants.DEFAULT_OBJECT_TYPE
    )
    event_activity_key = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, constants.DEFAULT_EVENT_ACTIVITY
    )

    # Build maps for faster lookup
    event_map = dict(
        zip(
            ocel.events[event_id_key],
            ocel.events[[event_timestamp_key, event_activity_key]].values,
        )
    )

    object_to_type_map = dict(
        zip(ocel.objects[object_id_key], ocel.objects[object_type_key])
    )

    event_to_objs_map = defaultdict(set)
    for e_id, o_id in ocel.relations[[event_id_key, object_id_key]].values:
        event_to_objs_map[e_id].add(o_id)

    return (event_map, object_to_type_map, event_to_objs_map)


def process_execution_fitting(occn: OCCausalNet, px: Collection[Tuple], stats: Optional[Dict] = None) -> bool:
    """
    Check whether a process execution fits the given OCCN

    Parameters

    -----------
    occn
        Object-centric causal net
    px
        A process execution in the format yielded by the
        preprocess_process_execution function

    Returns
    -----------
    bool
        Whether the process execution fits the OCCN
    """
    return _is_fitting(occn, px, OCCausalNetState(), 0, stats=stats)


def _is_fitting(
    occn: OCCausalNet, px: Collection[Tuple], state: OCCausalNetState, index: int, stats: Optional[Dict] = None
) -> bool:
    """
    Check whether a process execution fits the given OCCN
    Assumes that events for start and end activities only produce/consume
    obligations for one object at a time.

    Parameters

    -----------
    occn
        Object-centric causal net
    px
        A process execution in the format yielded by the
        preprocess_process_execution function
    state
        Current OCCN state
    index
        Current index in the process execution

    Returns
    -----------
    bool
        Whether the process execution fits the OCCN
    """
    if index >= len(px):
        # Success if we are in the empty state
        return not state.activities
    
    if stats is not None:
        stats["calls"] += 1 

    activity, obj_type_to_obj_ids = px[index]
    objects = set()
    for obj_ids in obj_type_to_obj_ids:
        objects.update(obj_ids[1])

    # Compute all possible bindings for the activity given the state and objects
    if activity.startswith("START_"):
        ot = next(iter(obj_type_to_obj_ids))[0]
        bindings = OCCausalNetSemantics.enabled_bindings_start_activity(
            occn, activity, ot, objects
        )
    else:
        bindings = OCCausalNetSemantics.enabled_bindings(
            occn, activity, state, objects=objects
        )

    # Prune bindings based on knowledge about the rest of the px
    # bindings = _prune_bindings(occn, px, index, bindings) # For future implementation

    for binding in bindings:
        new_state = OCCausalNetSemantics.bind_activity(
            occn,
            act=binding[0],
            cons=OCCausalNetSemantics.convert_binding_tuple_to_dict(binding[1]),
            prod=OCCausalNetSemantics.convert_binding_tuple_to_dict(binding[2]),
            state=state,
        )
        if _is_fitting(occn, px, new_state, index + 1, stats=stats):
            return True

    return False


def _prune_bindings(
    occn: OCCausalNet, px: Collection[Tuple], index: int, bindings: Collection[Tuple]
) -> Collection[Tuple]:
    """
    Prune the bindings based on the process execution and the current index.

    Parameters
    -----------
    occn
        Object-centric causal net
    px
        A process execution in the format yielded by the
        preprocess_process_execution function
    index
        Current index in the process execution
    bindings
        Current bindings to prune

    Returns
    -----------
    Collection[Tuple]
        Pruned bindings
    """
    memo_cons = {}
    memo_prod = {}
    filtered_bindings = []

    for binding in bindings:
        if binding[1] not in memo_cons:
            memo_cons[binding[1]] = _prune_consumed(occn, binding[1])
        if not memo_cons[binding[1]] and binding[2] not in memo_prod:
            memo_prod[binding[2]] = _prune_produced(occn, binding[2])

        if not memo_cons[binding[1]] and not memo_prod[binding[2]]:
            filtered_bindings.append(binding)

    return filtered_bindings


def _prune_consumed(occn: OCCausalNet, consumed: Tuple) -> bool:
    """
    Prune consumed obligations based on the causal net.

    Parameters
    -----------
    occn
        Object-centric causal net
    consumed
        Consumed obligations to prune

    Returns
    -----------
    bool
        True if the consumed obligations lead to a deadlock, False otherwise
    """
    # For future implementation
    return False


def _prune_produced(occn: OCCausalNet, produced: Tuple) -> bool:
    """
    Prune produced obligations based on the causal net.

    Parameters
    -----------
    occn
        Object-centric causal net
    produced
        produced obligations to prune

    Returns
    -----------
    bool
        True if the produced obligations lead to a deadlock, False otherwise
    """
    # For future implementation
    return False

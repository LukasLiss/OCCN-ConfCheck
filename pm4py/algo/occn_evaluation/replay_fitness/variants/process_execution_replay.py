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

from enum import Enum
from typing import Any, Collection, Dict, Optional, Tuple
from pm4py.util import exec_utils
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.oc_causal_net.semantics import OCCausalNetState, OCCausalNetSemantics
from pm4py.objects.ocel.util import process_executions


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    PROCESS_EXECUTION_EXTRACTION = "process_execution_extraction"


def apply(
    ocel: OCEL,
    oc_causal_net: OCCausalNet,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply process execution replay fitness evaluation.
    Assumes that start and end activities are capable of producing/consuming
    obligations for one object at a time.

    Parameters
    -----------
    ocel
        OCEL to evaluate
    oc_causal_net
        Causal net
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

    process_execution_extraction = exec_utils.get_param_value(
        Parameters.PROCESS_EXECUTION_EXTRACTION,
        parameters,
        "connected_components",
    )

    # Derive process executions
    px_results = process_executions.apply(
        ocel, variant=process_execution_extraction, parameters=parameters
    )
    pxs = px_results["process_executions"]

    total = 0
    fitting = 0

    # Compute fitness
    for px in pxs:
        px_processed = preprocess_process_execution(ocel, px, parameters=parameters)
        if process_execution_fitting(
            oc_causal_net, px_processed, parameters=parameters
        ):
            fitting += 1
        total += 1

    log_fitness = fitting / total if total > 0 else 0.0

    return {"log_fitness": log_fitness, "no_process_executions": len(pxs)}


def preprocess_process_execution(
    ocel: OCEL,
    process_execution: Collection[Any],
    parameters: Optional[Dict[Any, Any]] = None,
) -> Collection[Tuple]:
    """
    Preprocess a process execution into a list of (activity, object_type to object_ids mapping) tuples

    Parameters
    -----------
    ocel
        Object-centric event log
    process_execution
        A collection of events ids representing a process execution

    Returns
    -----------
    collection
        Preprocessed process execution.
        Tuples of form (activity, object_type to object_ids mapping) where
        object_type to object_ids mapping is represented as a frozenset
        of (object_type, frozenset(object_ids)) pairs
    """
    event_timestamp_key = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP,
        parameters,
        constants.DEFAULT_EVENT_TIMESTAMP,
    )
    object_id_key = exec_utils.get_param_value(
        Parameters.OBJECT_ID,
        parameters,
        constants.DEFAULT_OBJECT_ID,
    )
    object_type_key = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE,
        parameters,
        constants.DEFAULT_OBJECT_TYPE,
    )
    event_activity_key = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY,
        parameters,
        constants.DEFAULT_EVENT_ACTIVITY,
    )

    # Preprocessing
    px = list(process_execution)
    # order by timestamp
    px.sort(key=lambda e: ocel.events[e][event_timestamp_key])
    px_new = []
    px_objects = dict()
    # add activity id & objects involved
    for e in px:
        activity = ocel.events[e][event_activity_key]
        objs = ocel.events[e][object_id_key]
        obj_by_type = {}
        for o in objs:
            obj_type = ocel.objects[o][object_type_key]
            obj_by_type[obj_type] = obj_by_type.get(obj_type, []) + [o]
        for ot in obj_by_type:
            px_objects[ot] = px_objects.get(ot, set()).union(set(obj_by_type[ot]))
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


def process_execution_fitting(occn: OCCausalNet, px: Collection[Tuple]) -> bool:
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
    return _is_fitting(occn, px, OCCausalNetState(), 0)


def _is_fitting(
    occn: OCCausalNet, px: Collection[Tuple], state: OCCausalNetState, index: int
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

    activity, obj_type_to_obj_ids = px[index]
    objects = set()
    for obj_ids in obj_type_to_obj_ids:
        objects.update(obj_ids[1])

    # Compute all possible bindings for the activity given the state and objects
    if activity.startswith("START_"):
        ot, _ = next(iter(obj_type_to_obj_ids.items()))
        bindings = OCCausalNetSemantics.enabled_bindings_start_activity(
            occn, activity, ot, objects
        )
    else:
        bindings = OCCausalNetSemantics.enabled_bindings(occn, activity, state, objects=objects)
        
    # Prune bindings based on knowledge about the rest of the px
    #bindings = _prune_bindings(occn, px, index, bindings) TODO enable and implement
    
    for binding in bindings:
        new_state = OCCausalNetSemantics.bind_activity(
            occn,
            act=binding[0],
            cons=OCCausalNetSemantics.convert_binding_tuple_to_dict(binding[1]),
            prod=OCCausalNetSemantics.convert_binding_tuple_to_dict(binding[2]),
            state=state,
        )
        if _is_fitting(occn, px, new_state, index + 1):
            return True

    return False

def _prune_bindings(occn: OCCausalNet, px: Collection[Tuple], index: int, bindings: Collection[Tuple]) -> Collection[Tuple]:
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
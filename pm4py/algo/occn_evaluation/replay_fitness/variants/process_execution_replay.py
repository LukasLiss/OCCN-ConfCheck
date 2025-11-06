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
    OCCN_SEMANTICS = "occn_semantics"
    PROCESS_EXECUTION_EXTRACTION = "process_execution_extraction"


def apply(
    ocel: OCEL,
    oc_causal_net: OCCausalNet,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply process execution replay fitness evaluation

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
        - Parameters.OCCN_SEMANTICS => the OCCN semantics to use (default: OCCausalNetSemantics)
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
    px_results = process_executions.apply(ocel, variant=process_execution_extraction, parameters=parameters)
    pxs = px_results["process_executions"]
    
    total = 0
    fitting = 0
    
    # Compute fitness
    for px in pxs:
        if process_execution_fitting(oc_causal_net, ocel, px, parameters=parameters):
            fitting += 1
        total += 1

    log_fitness = fitting / total if total > 0 else 0.0

    return {
        "log_fitness": log_fitness,
        "no_process_executions": len(pxs)
    }


def process_execution_fitting(occn: OCCausalNet, ocel: OCEL, process_execution: Collection[Any],parameters: Optional[Dict[Any, Any]] = None) -> bool:
    """
    Check whether a process execution fits the given OCCN

    Parameters
    
    -----------
    occn
        Object-centric causal net
    ocel
        Object-centric event log
    process_execution
        A collection of events ids representing a process execution

    Returns
    -----------
    bool
        Whether the process execution fits the OCCN
    """
    # Preprocessing
    # order by timestamp
    # get activityid & objects involved
    
    
    
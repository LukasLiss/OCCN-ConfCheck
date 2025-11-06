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
from typing import Any, Dict, Optional
from pm4py.util import exec_utils
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.oc_causal_net.semantics import OCCausalNetState, OCCausalNetSemantics


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    OCCN_SEMANTICS = "occn_semantics"


def apply(
    log: OCEL,
    oc_causal_net: OCCausalNet,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply process execution replay fitness evaluation

    Parameters
    -----------
    log
        OCEL to evaluate
    oc_causal_net
        Causal net
    parameters
        Parameters

    Returns
    -----------
    dictionary
        Results of the fitness evaluation:
            - 'log_fitness': overall fitness value (between 0 and 1)
    """
    if parameters is None:
        parameters = {}
        
    semantics = exec_utils.get_param_value(
        Parameters.OCCN_SEMANTICS,
        parameters,
        OCCausalNetSemantics(),
    )
    event_id_column = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, constants.DEFAULT_EVENT_ID
    )
    object_id_column = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, constants.DEFAULT_OBJECT_ID
    )
    object_type_column = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, constants.DEFAULT_OBJECT_TYPE
    )
    event_activity = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, constants.DEFAULT_EVENT_ACTIVITY
    )
    event_timestamp = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, constants.DEFAULT_EVENT_TIMESTAMP
    )
    
    log_fitness = log_fitness(oc_causal_net, log)
    

def log_fitness(occn: OCCausalNet, ocel: OCEL) -> float:
    """
    Compute the log fitness value

    Parameters
    -----------
    occn
        Object-centric causal net
    ocel
        Object-centric event log

    Returns
    -----------
    float
        Log fitness value (between 0 and 1)
    """
    pass
    
    
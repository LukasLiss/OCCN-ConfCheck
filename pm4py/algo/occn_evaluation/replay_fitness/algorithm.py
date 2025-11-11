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

from pm4py.algo.occn_evaluation.replay_fitness.variants import process_execution_replay
from pm4py.util import exec_utils
from enum import Enum
from typing import Optional, Dict, Any
from pm4py.objects.ocel.obj import OCEL  
from pm4py.objects.oc_causal_net.obj import OCCausalNet


class Variants(Enum):
    PROCESS_EXECUTION_REPLAY = process_execution_replay



PROCESS_EXECUTION_REPLAY = Variants.PROCESS_EXECUTION_REPLAY

DEFAULT_VARIANT = Variants.PROCESS_EXECUTION_REPLAY
VERSIONS = {PROCESS_EXECUTION_REPLAY}


def apply(
    occn: OCCausalNet,
    ocel: OCEL,
    parameters: Optional[Dict[Any, Any]] = None,
    variant=DEFAULT_VARIANT,
) -> Dict[str, Any]:
    """
    Apply fitness evaluation starting from an event log and an object-centric causal net,
    by using one of the replay techniques provided by PM4Py

    Parameters
    -----------
    ocel
        OCEL to evaluate
    occn
        Object-centric causal net
    parameters
        Parameters related to the replay algorithm
    variant
        Chosen variant:
            - Variants.PROCESS_EXECUTION_REPLAY

    Returns
    ----------
    dictionary
        Results of the fitness evaluation:
            - 'log_fitness': overall fitness value (between 0 and 1)
            - 'no_process_executions': number of process executions derived from the log
    """
    if parameters is None:
        parameters = {}

    return exec_utils.get_variant(variant).apply(occn=occn, ocel=ocel, parameters=parameters)
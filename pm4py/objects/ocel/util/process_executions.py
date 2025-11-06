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
import networkx as nx
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.util import exec_utils
from typing import Optional, Dict, Any
from enum import Enum

class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE


def apply(ocel: OCEL, variant: str, parameters: Optional[Dict[Any, Any]] = None):
    """
        Extract process executions from an OCEL. Based on Adams et al. "Defining 
        Cases and Variants for Object-Centric Event Data" (2022). Implementation
        adapted from OCPA v1.1.

        Parameters
        ---------------
        ocel
            Object-centric event log
        variant
            Variant of process execution extraction:
                - "connected_components": extracts process executions as connected components in the event-object graph
        parameters
            Parameters of the algorithm, including:
            - Parameters.EVENT_ID => the event identifier column
            - Parameters.EVENT_ACTIVITY => the event activity column
            - Parameters.EVENT_TIMESTAMP => the event timestamp column
            - Parameters.OBJECT_ID => the object identifier column
            - Parameters.OBJECT_TYPE => the object type column

        Returns
        --------------
        tuple
            A tuple with three elements:
            - process_executions: List of process executions, each represented as a set of event ids
            - object_mapping: List of lists denoting objects per process execution id
            - px_mapping: Dictionary mapping events to process execution ids
    """
    if parameters is None:
        parameters = {}
    
    if variant == "connected_components":
        return connected_components(ocel, parameters=parameters)
    else:
        raise ValueError(f"Variant {variant} not recognized.")
    


def connected_components(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None):
    """
    Extract process executions from an OCEL using the connected components 
    extraction. In this method, process executions are defined as connected 
    components in the event-object graph.
    """
    event_id = exec_utils.get_param_value(Parameters.EVENT_ID, parameters, ocel.event_id_column)
    object_id = exec_utils.get_param_value(Parameters.OBJECT_ID, parameters, ocel.object_id_column)
    
    # mapping events to process execution ids
    px_mapping = {}
    # objects per process execution id
    object_mapping = []
    
    # Create bipartite graph based on OCEL relations. This graph has the same connected
    # components as the event-object graph.
    G = nx.Graph()
    edges = ocel.relations[[event_id, object_id]].values
    G.add_edges_from(edges)
    
    # Extract connected components
    event_ids = set(ocel.events[event_id])
    object_ids = set(ocel.objects[object_id])
    process_executions = []
    for component in nx.connected_components(G):
        component_events = component.intersection(event_ids)
        component_objects = component.intersection(object_ids)
        if component_events:
            process_executions.append(component_events)
            object_mapping.append(component_objects)
            for event in component_events:
                px_mapping[event] = len(process_executions) - 1

    return {
        "process_executions": process_executions,
        "object_mapping": object_mapping,
        "px_mapping": px_mapping
    }
    
    
'''
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
'''

import json
import uuid


def apply(ocpn, file_path: str, parameters=None):
    """
    Serializes an OCPetriNet object to a generic JSON file.
    This serialization abstracts from PM4Py specifics to allow easier
    interoperability with other tools that support OCPN.
    Marking information may be lost if multiple tokens per place are used.

    Parameters
    ------------
    ocpn
        OCPetriNet object to serialize
    file_path
        The path to save the JSON file.
    parameters
        Possible parameters of the algorithm
    """
    if parameters is None:
        parameters = {}
    
    # Helper to generate unique IDs for objects 
    # We map python object id() -> UUID string
    obj_id_map = {}

    def get_id(obj):
        if id(obj) not in obj_id_map:
            obj_id_map[id(obj)] = str(uuid.uuid4())
        return obj_id_map[id(obj)]

    # Analyze Markings to determine Initial/Final status of places
    initial_place_names = set()
    if ocpn.initial_marking:
        for p in ocpn.initial_marking.keys():
            initial_place_names.add(p.name)
            
    final_place_names = set()
    if ocpn.final_marking:
        for p in ocpn.final_marking.keys():
            final_place_names.add(p.name)

    # Serialize Places
    serialized_places = []
    for p in ocpn.places:
        p_id = get_id(p)
        serialized_places.append({
            "id": p_id,
            "name": p.name,
            "object_type": p.object_type,
            "is_initial": p.name in initial_place_names,
            "is_final": p.name in final_place_names,
            "properties": p.properties if p.properties else {}
        })

    # Serialize Transitions
    serialized_transitions = []
    for t in ocpn.transitions:
        t_id = get_id(t)
        is_silent = t.label is None
        serialized_transitions.append({
            "id": t_id,
            "name": t.name,
            "label": t.label if t.label else t.name,
            "silent": is_silent,
            "properties": t.properties if t.properties else {}
        })

    # Serialize Arcs
    serialized_arcs = []
    for arc in ocpn.arcs:
        obj_type = getattr(arc, "object_type", None) 
        is_var = getattr(arc, "is_variable", False)

        serialized_arcs.append({
            "id": str(uuid.uuid4()), 
            "source_id": get_id(arc.source),
            "target_id": get_id(arc.target),
            "object_type": obj_type,
            "variable": is_var,
            "weight": arc.weight,
            "properties": arc.properties if arc.properties else {}
        })

    # Construct final Dict
    data = {
        "protocol": "OCPN_JSON_BRIDGE_1.0",
        "net": {
            "name": ocpn.name,
            "properties": ocpn.properties if ocpn.properties else {}
        },
        "places": serialized_places,
        "transitions": serialized_transitions,
        "arcs": serialized_arcs
    }

    # Write to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    print(f"Successfully serialized PM4Py OCPN to {file_path}")

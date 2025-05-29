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

from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.ocpn.obj import OCPetriNet
import networkx as nx


def apply(ocpn: OCPetriNet, parameters=None) -> OCCausalNet:
    """
    Convets an Object-centric Petri Net to an Object-centric Causal Net.

    Parameters
    ----------
    ocpn: OCPetriNet
        The Object-centric Petri Net to be converted.
    parameters: dict, optional
        Additional parameters for the conversion (not used in this implementation).

    Returns
    ----------
    OCCausalNet: OCCausalNet
        The resulting Object-centric Causal Net.
    """
    places = ocpn.places
    transitions = ocpn.transitions
    object_types = ocpn.object_types

    dependencies = dict()
    input_marker_groups = dict()
    output_marker_groups = dict()

    # create dependencies and marker groups for transitions
    transition_dependencies_marker_groups(
        transitions, dependencies, input_marker_groups, output_marker_groups
    )

    # create dependencies and marker groups for places
    place_dependencies_marker_groups(
        places, dependencies, input_marker_groups, output_marker_groups
    )

    # handle start and end places
    start_places = {
        ot: [p for p in ocpn.initial_marking.places if p.object_type == ot]
        for ot in ocpn.object_types
    }
    end_places = {
        ot: [p for p in ocpn.final_marking.places if p.object_type == ot]
        for ot in ocpn.object_types
    }

    # add START and END activities and their dependencies and marker groups
    start_end_act_dependencies_marker_groups(
        object_types,
        dependencies,
        input_marker_groups,
        output_marker_groups,
        start_places,
        end_places,
    )

    # add START and END activities to marker groups of start and end places
    add_start_end_act_markers(
        object_types,
        input_marker_groups,
        output_marker_groups,
        start_places,
        end_places,
    )

    # create the occn
    occn = OCCausalNet(
        dependency_graph=nx.MultiDiGraph(dependencies),
        output_marker_groups=output_marker_groups,
        input_marker_groups=input_marker_groups,
    )

    return occn


def transition_dependencies_marker_groups(
    transitions, dependencies, input_marker_groups, output_marker_groups
):
    """
    Creates dependencies and marker groups for transitions in the Object-centric Petri Net.
    Each transition has one input marker group featuring a marker for each input arc,
    and one output marker group featuring a marker for each output arc.

    Parameters
    ----------
    transitions: list
        List of transitions in the Object-centric Petri Net.
    dependencies: dict
        Dictionary to store dependencies between activities.
    input_marker_groups: dict
        Dictionary to store input marker groups.
    output_marker_groups: dict
        Dictionary to store output marker groups.
    """
    for t in transitions:
        # dependencies
        dependencies[t.name] = dict()  # add as activity
        for arc in t.in_arcs:
            add_dependency(dependencies, arc.source, t, arc.object_type)
        for arc in t.out_arcs:
            add_dependency(dependencies, t, arc.target, arc.object_type)

        # single input marker group
        input_marker_groups[t.name] = [
            OCCausalNet.MarkerGroup(
                [
                    OCCausalNet.Marker(
                        related_activity=arc.source.name,
                        object_type=arc.object_type,
                        count_range=(0, float('inf')) if arc.is_variable else (1, 1),
                        marker_key=get_next_key(),
                    )
                    for arc in t.in_arcs
                ]
            )
        ]

        # single output marker group
        output_marker_groups[t.name] = [
            OCCausalNet.MarkerGroup(
                [
                    OCCausalNet.Marker(
                        related_activity=arc.target.name,
                        object_type=arc.object_type,
                        count_range=(0, float('inf')) if arc.is_variable else (1, 1),
                        marker_key=get_next_key(),
                    )
                    for arc in t.out_arcs
                ]
            )
        ]


def place_dependencies_marker_groups(
    places, dependencies, input_marker_groups, output_marker_groups
):
    """
    Creates dependencies and marker groups for places in the Object-centric Petri Net.
    Each place has one input marker group per input arc having one marker each,
    and one output marker group per output arc having one marker each.

    Parameters
    ----------
    places: list
        List of places in the Object-centric Petri Net.
    dependencies: dict
        Dictionary to store dependencies between activities.
    input_marker_groups: dict
        Dictionary to store input marker groups.
    output_marker_groups: dict
        Dictionary to store output marker groups.
    """
    for p in places:
        # dependencies
        dependencies[p.name] = dict()  # add as activity
        for arc in p.in_arcs:
            add_dependency(dependencies, arc.source, p, arc.object_type)
        for arc in p.out_arcs:
            add_dependency(dependencies, p, arc.target, arc.object_type)

        # one-element marker group per arc
        input_marker_groups[p.name] = [
            OCCausalNet.MarkerGroup(
                [OCCausalNet.Marker(
                    related_activity=arc.source.name,
                    object_type=arc.object_type,
                    count_range=(1, float('inf')),
                    marker_key=get_next_key(),
                )]
            )
            for arc in p.in_arcs
        ]

        output_marker_groups[p.name] = [
            OCCausalNet.MarkerGroup(
                [OCCausalNet.Marker(
                    related_activity=arc.target.name,
                    object_type=arc.object_type,
                    count_range=(1, float('inf')),
                    marker_key=get_next_key(),
                )]
            )
            for arc in p.out_arcs
        ]


def start_end_act_dependencies_marker_groups(
    object_types,
    dependencies,
    input_marker_groups,
    output_marker_groups,
    start_places,
    end_places,
):
    """
    Adds a START and END activity for each object type.
    Creates dependencies and marker groups for those new activities.
    Each START / END activity has one input / output marker group consisting
    of markers for every start / end place.

    Parameters
    ----------
    object_types: list
        List of object types in the Object-centric Petri Net.
    dependencies: dict
        Dictionary to store dependencies between activities.
    input_marker_groups: dict
        Dictionary to store input marker groups.
    output_marker_groups: dict
        Dictionary to store output marker groups.
    start_places: dict
        Dictionary mapping object types to their start places.
    end_places: dict
        Dictionary mapping object types to their end places.
    """
    for ot in object_types:
        # START places
        dependencies[f"START_{ot}"] = dict()
        for p in start_places[ot]:
            add_dependency(dependencies, f"START_{ot}", p, ot)

        # one output marker group
        output_marker_groups[f"START_{ot}"] = [
            OCCausalNet.MarkerGroup(
                [
                    OCCausalNet.Marker(
                        related_activity=p.name,
                        object_type=ot,
                        count_range=(1, float('inf')),
                        marker_key=get_next_key(),
                    )
                    for p in start_places[ot]
                ]
            )
        ]

        # END places
        dependencies[f"END_{ot}"] = dict()
        for p in end_places[ot]:
            add_dependency(dependencies, p, f"END_{ot}", ot)

        # one input marker group
        input_marker_groups[f"END_{ot}"] = [
            OCCausalNet.MarkerGroup(
                [
                    OCCausalNet.Marker(
                        related_activity=p.name,
                        object_type=ot,
                        count_range=(1, float('inf')),
                        marker_key=get_next_key(),
                    )
                    for p in end_places[ot]
                ]
            )
        ]


def add_start_end_act_markers(
    object_types, input_marker_groups, output_marker_groups, start_places, end_places
):
    """
    Adds markers for the START and END activities to the start / end places.
    These markers are the same as for any other predecessor / successor activity.

    Parameters
    ----------
    object_types: list
        List of object types in the Object-centric Petri Net.
    input_marker_groups: dict
        Dictionary to store input marker groups.
    output_marker_groups: dict
        Dictionary to store output marker groups.
    start_places: dict
        Dictionary mapping object types to their start places.
    end_places: dict
        Dictionary mapping object types to their end places.
    """
    for ot in object_types:
        for p in start_places[ot]:
            # add new marker group
            if p.name not in input_marker_groups:
                input_marker_groups[p.name] = []
            input_marker_groups[p.name].append(
                OCCausalNet.MarkerGroup(
                    [
                        OCCausalNet.Marker(
                            related_activity=f"START_{ot}",
                            object_type=ot,
                            count_range=(1, float('inf')),
                            marker_key=get_next_key(),
                        )
                    ]
                )
            )
        for p in end_places[ot]:
            # add new marker group
            if p.name not in output_marker_groups:
                output_marker_groups[p.name] = []
            output_marker_groups[p.name].append(
                OCCausalNet.MarkerGroup(
                    [
                        OCCausalNet.Marker(
                            related_activity=f"END_{ot}",
                            object_type=ot,
                            count_range=(1, float('inf')),
                            marker_key=get_next_key(),
                        )
                    ]
                )
            )


def add_dependency(dependencies: dict, source, target, object_type):
    """
    Adds a dependency to the dependencies dictionary. Ignores duplicate dependencies.

    Parameters
    ----------
    dependencies: dict
        The dictionary to which the dependency will be added.
    source: str or OCPetriNet.Place or OCPetriNet.Transition
        The source of the dependency arc.
    target str or OCPetriNet.Place or OCPetriNet.Transition
        The target of the dependency arc.
    object_type
        The object type associated with the dependency.
    """
    source_label = source if isinstance(source, str) else source.name
    target_label = target if isinstance(target, str) else target.name
    if source_label not in dependencies:
        dependencies[source_label] = dict()
    if target_label not in dependencies[source_label]:
        dependencies[source_label][target_label] = dict()
    if object_type not in dependencies[source_label][target_label]:
        dependencies[source_label][target_label][object_type] = {
            "object_type": object_type
        }


def get_next_key():
    """
    Will return a unique key for each call, starting from 0.
    """
    # initialize on first call
    if not hasattr(get_next_key, "counter"):
        get_next_key.counter = 0
    current = get_next_key.counter
    get_next_key.counter += 1
    return current

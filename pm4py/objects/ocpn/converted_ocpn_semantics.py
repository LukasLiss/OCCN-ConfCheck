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
import re
from typing import Counter, TypeVar

from pm4py.objects.ocpn.obj import OCMarking, OCPetriNet
from pm4py.objects.ocpn.semantics import OCPetriNetSemantics
from pm4py.algo.simulation.playout.ocpn.variants.extensive import (
    apply as ocpn_extensive_playout,
)


N = TypeVar("N", bound=OCPetriNet)


class ConvertedOCPetriNetSemantics(OCPetriNetSemantics[N]):

    @classmethod
    def _is_final(cls, marking: OCMarking, final_marking: OCMarking) -> bool:
        """
        Overrides the method to check if the marking is final.
        A marking is considered final if it only contains objects in the places
        that are part of the final marking, and all other places are empty.

        Parameters
        ----------
        marking: OCMarking
            The marking to check
        final_marking: OCMarking
            The final marking to compare against

        Returns
        -------
        bool
            True if the marking is final, False otherwise
        """
        return marking.places <= final_marking.places

    @classmethod
    def precompute_ocpn_replay_params(cls, ocpn, occn):
        """
        Precomputes parameters needed for the `replay_occn_sequence` function.

        Parameters
        ----------
        ocpn: N
            The OCPN to replay on
        occn: N
            The OCCN that was converted to the OCPN

        Returns
        -------
        dict
            A dictionary containing precomputed parameters for replaying OCCN sequences on the OCPN
            - "start_activities": Set of activities that are start activities in the OCCN
            - "end_activities": Set of activities that are end activities in the OCCN
            - "start_input_places": Mapping from start activities to their input place in the OCPN
            - "end_output_places": Mapping from end activities to their output place in the OCPN
            - "subnet": Mapping from activities to the subnet of the OCPN that corresponds to the activity (including the global binding place)
            - "arc_places": Mapping from (activity, object type, successor activity) to the corresponding arc place in the OCPN
            - "global_binding_place": The global binding place in the OCPN
        """
        # ----- OCCN attributes -----
        start_activities = set(
            act for act in occn.activities if act.startswith("START_")
        )
        end_activities = set(act for act in occn.activities if act.startswith("END_"))

        # ----- OCPN attributes -----
        start_input_places = {}
        end_output_places = {}
        arc_places = {}
        global_binding_place = None

        binding_object_type = "_binding"
        start_input_place_pattern = re.compile(r"^p_START_(.+?)_i_\1$")
        end_output_place_pattern = re.compile(r"^p_END_(.+?)_o_\1$")
        arc_place_pattern = re.compile(r"^p_arc\(([^,]+),([^)]+)\)_(.+)$")

        for place in ocpn.places:
            if place.name == f"p{binding_object_type}_global_input":
                global_binding_place = place
                continue

            arc_place_match = arc_place_pattern.fullmatch(place.name)
            if arc_place_match:
                pred_act = arc_place_match.group(1)
                succ_act = arc_place_match.group(2)
                ot = arc_place_match.group(3)
                arc_places[(pred_act, ot, succ_act)] = place
                continue

            start_input_place_match = start_input_place_pattern.fullmatch(place.name)
            if start_input_place_match:
                object_type = start_input_place_match.group(1)
                start_input_places["START_" + object_type] = place
                continue

            end_output_place_match = end_output_place_pattern.fullmatch(place.name)
            if end_output_place_match:
                object_type = end_output_place_match.group(1)
                end_output_places["END_" + object_type] = place
                continue

        # ----- OCPN subnets -----
        subnets = dict()
        for act in occn.activities:
            subnets[act] = cls._get_ocpn_subnet(
                act,
                global_binding_place,
                arc_places,
                start_activities,
                end_activities,
                start_input_places,
                end_output_places,
            )

        return {
            "start_activities": start_activities,
            "end_activities": end_activities,
            "start_input_places": start_input_places,
            "end_output_places": end_output_places,
            "arc_places": arc_places,
            "subnet": subnets,
            "global_binding_place": global_binding_place,
        }

    @classmethod
    def _get_ocpn_subnet(
        cls,
        activity: str,
        global_binding_place: OCPetriNet.Place,
        arc_places: dict,
        start_activities: set,
        end_activities: set,
        start_input_places: dict,
        end_output_places: dict,
    ) -> OCPetriNet:
        """
        Computes the subnet of ocpn that contains all places and transitions
        on a path from the arc places towards activity to the arc places from activity.
        This includes the global binding place but not places and transitions
        reachable from the arc places through the global binding place.

        Parameters
        ----------
        activity: str
            The activity for which to compute the subnet
        global_binding_place: OCPetriNet.Place
            The global binding place in the OCPN
        arc_places: dict
            Mapping from (activity, object type, successor activity) to the corresponding arc place in the OCPN
        start_activities: set
            Set of start activities in the OCCN
        end_activities: set
            Set of end activities in the OCCN
        start_input_places: dict
            Mapping from start activities to their input place in the OCPN
        end_output_places: dict
            Mapping from end activities to their output place in the OCPN

        Returns
        -------
        OCPetriNet
            The subnet of the OCPN that corresponds to the activity
        """
        places = set()
        transitions = set()
        arcs = set()

        # source arc places towards activity
        source_arc_places = set()
        # target arc places from activity
        target_arc_places = set()
        for (source, _, target), place in arc_places.items():
            if source == activity:
                target_arc_places.add(place)
            elif target == activity:
                source_arc_places.add(place)

        if activity in start_activities:
            # has no source arc places
            source_arc_places = set([start_input_places[activity]])
        if activity in end_activities:
            # has no target arc places
            target_arc_places = set([end_output_places[activity]])

        places.update(source_arc_places)
        places.update(target_arc_places)
        places.add(global_binding_place)

        # We do a BFS to find all places and transitions
        to_visit = set(source_arc_places)

        visited = set()
        visited.update(to_visit)
        # we do not want to visit the global binding place as it is connected to
        # places and transitions that are not part of the subnet
        visited.add(global_binding_place)
        # we want to stop at the target arc places
        visited.update(target_arc_places)

        while to_visit:
            current = to_visit.pop()

            for arc in current.out_arcs:
                arcs.add(arc)
                target = arc.target
                if target not in visited:
                    if isinstance(target, OCPetriNet.Place):
                        places.add(target)
                    elif isinstance(target, OCPetriNet.Transition):
                        transitions.add(target)

                    to_visit.add(target)
                    visited.add(target)

        subnet = OCPetriNet(
            name=f"SUBNET_{activity}",
            places=places,
            transitions=transitions,
            arcs=arcs,
        )

        return subnet

    @classmethod
    def replay_occn_sequence(
        cls,
        sequence,
        initial_marking: OCMarking,
        final_marking: OCMarking,
        id_to_activity,
        id_to_object_type,
        precomputed,
    ):
        """
        Replay a sequence of the OCCN on the converted OCPN.
        Will consider any marking as final that contains only objects in the places
        that are part of the final marking, and all other places are empty.

        Parameters
        ----------
        sequence: tuple of Binding
            The sequence to replay
        initial_marking: OCMarking
            The initial marking of the OCPN
        final_marking: OCMarking
            The final marking of the OCPN
        id_to_activity: dict
            Mapping from activity IDs to activity names
        id_to_object_type: dict
            Mapping from object IDs to object types
        precomputed: dict
            Precomputed parameters for the replay obtained from `precompute_ocpn_replay_params`

        Returns
        -------
        bool
            True if the sequence was successfully replayed, False otherwise
        """
        start_activities = precomputed["start_activities"]
        end_activities = precomputed["end_activities"]
        arc_places = precomputed["arc_places"]
        start_input_places = precomputed["start_input_places"]
        end_output_places = precomputed["end_output_places"]
        subnets = precomputed["subnet"]
        global_binding_place = precomputed["global_binding_place"]

        # Start in initial marking
        marking = initial_marking.copy()

        # Keep track of start activity tokens that we assume to be valid
        # We check this at the very end
        start_expected_tokens = defaultdict(OCMarking)
        start_target_tokens = defaultdict(OCMarking)

        # Same for end activities
        end_expected_tokens = defaultdict(OCMarking)
        end_target_tokens = defaultdict(OCMarking)

        for act_id, consumed, produced in sequence:
            act = id_to_activity[act_id]
            # Ignore start and end activities
            if act in start_activities or act in end_activities:
                continue

            # Parse consumed and produced to dicts
            consumed_objects = {
                (pred_id, ot_id): objects
                for (pred_id, ot_to_obj) in consumed
                for ot_id, objects in ot_to_obj
            }
            produced_objects = {
                (succ_id, ot_id): objects
                for (succ_id, ot_to_obj) in produced
                for ot_id, objects in ot_to_obj
            }

            # For start activities in predecessors, move the tokens from their
            # input place to the arc place towards act
            # this does not check if these moves are valid. 
            marking = cls._bind_start_activities(
                marking,
                act,
                start_activities,
                start_input_places,
                consumed_objects,
                id_to_activity,
                id_to_object_type,
                arc_places,
                start_expected_tokens,
                start_target_tokens,
            )
            if marking is None:
                return False

            # All tokens in consumed_objects should be on the arc from pred_id to act_id (with ot_id)

            # What we expect to find in the marking
            expected_tokens = OCMarking(
                {
                    arc_places[
                        (id_to_activity[pred_id], id_to_object_type[ot_id], act)
                    ]: Counter(objects)
                    for (pred_id, ot_id), objects in consumed_objects.items()
                }
            )

            # What we want to achieve by a firing sequence with act
            target_tokens = OCMarking(
                {
                    arc_places[
                        (act, id_to_object_type[ot_id], id_to_activity[succ_id])
                    ]: Counter(objects)
                    for (succ_id, ot_id), objects in produced_objects.items()
                }
            )

            # Check if the marking contains the expected tokens
            if not cls._is_submarking(expected_tokens, marking):
                return False

            # Check if we can reach the target tokens from the expected tokens
            marking = cls._simulate_binding(
                marking,
                act,
                expected_tokens,
                target_tokens,
                subnets,
                global_binding_place,
            )
            if marking is None:
                return False

            # For end activities in successors, move the tokens from the arc place
            # towards its output place
            marking = cls._bind_end_activities(
                marking,
                act,
                end_activities,
                end_output_places,
                produced_objects,
                id_to_activity,
                id_to_object_type,
                arc_places,
                subnets,
                global_binding_place,
            )
            if not marking:
                return False

        # Check if all the start activitiy moves were valid
        for start_act, expected_tokens in start_expected_tokens.items():
            target_tokens = start_target_tokens[start_act]
            if not cls._is_submarking(expected_tokens, marking):
                return False

            # Check if we can reach the target tokens from the expected tokens
            if not cls._simulate_binding(
                initial_marking,
                start_act,
                expected_tokens,
                target_tokens,
                subnets,
                global_binding_place,
            ):
                return False
        
        # Check if all the end activity moves were valid
        for end_act, expected_tokens in end_expected_tokens.items():
            target_tokens = end_target_tokens[end_act]
            if not cls._is_submarking(expected_tokens, marking):
                return False

            # Check if we can reach the target tokens from the expected tokens
            if not cls._simulate_binding(
                initial_marking,
                end_act,
                expected_tokens,
                target_tokens,
                subnets,
                global_binding_place,
            ):
                return False
        
        # Check if we are in a final marking
        success = cls._is_final(marking, final_marking)
        return success

    @classmethod
    def _bind_start_activities(
        cls,
        marking: OCMarking,
        act: str,
        start_activities: set,
        start_input_places: dict,
        consumed_objects: dict,
        id_to_activity: dict,
        id_to_object_type: dict,
        arc_places: dict,
        start_target_tokens: defaultdict,
    ):
        """
        For all predecessors in consumed_objects that are start activities, move the corresponding tokens
        from the start activity's input place to the arc place towards the act_id.
        Does not check if these moves are valid.
        Stores all moves performed in start_expected_tokens and start_target_tokens
        to allow for a later check once all start activities have been processed.

        Parameters
        ----------
        marking: OCMarking
            The current marking of the OCPN
        act: str
            The activity to move the token towards
        start_activities: set
            Set of start activities in the OCCN
        start_input_places: dict
            Mapping from start activities to their input place in the OCPN
        consumed_objects: dict
            The objects to bind the start activities with
        id_to_activity: dict
            Mapping from activity IDs to activity names
        id_to_object_type: dict
            Mapping from object IDs to object types
        arc_places: dict
            Mapping from (activity, object type, successor activity) to the corresponding arc place in the OCPN
        start_target_tokens: defaultdict
            A dictionary to store target tokens for start activities

        Returns
        -------
        OCMarking or None
            The updated marking after moving tokens for the start activity
            Or None if the required tokens are not available
        """
        for (pred_id, ot_id), objects in consumed_objects.items():
            start_act = id_to_activity[pred_id]
            if start_act not in start_activities:
                continue

            # Target tokens in the arc place towards act
            target_tokens = OCMarking(
                {
                    arc_places[(start_act, id_to_object_type[ot_id], act)]: Counter(
                        objects
                    )
                }
            )

            # Create the tokens without knowing if the binding is valid
            marking += target_tokens
            
            # Keep track to later check if all start bindings together were valid
            start_target_tokens[start_act] += target_tokens

        return marking

    @classmethod
    def _bind_end_activities(
        cls,
        marking: OCMarking,
        act: str,
        end_activities: set,
        end_output_places: dict,
        produced_objects: dict,
        id_to_activity: dict,
        id_to_object_type: dict,
        arc_places: dict,
        subnets: dict,
        global_binding_place: OCPetriNet.Place,
        end_expected_tokens: defaultdict,
        end_target_tokens: defaultdict,
    ):
        """
        For all successors in produced_objects that are end activities,
        move the corresponding tokens from the arc place towards the end activity's output place.
        Does not check if these moves are valid.
        Stores all moves performed in end_expected_tokens and end_target_tokens
        to allow for a later check once all end activities have been processed.

        Parameters
        ----------
        marking: OCMarking
            The current marking of the OCPN
        act: str
            The activity to move the token from
        end_activities: set
            Set of end activities in the OCCN
        end_output_places: dict
            Mapping from end activities to their output place in the OCPN
        produced_objects: dict
            The objects to bind the end activities with
        id_to_activity: dict
            Mapping from activity IDs to activity names
        id_to_object_type: dict
            Mapping from object IDs to object types
        arc_places: dict
            Mapping from (activity, object type, successor activity) to the corresponding arc place in the OCPN
        subnets: dict
            Mapping from activity names to their respective subnets in the OCPN
        global_binding_place: OCPetriNet.Place
            The global binding place in the OCPN, where the _binding token is added.
        end_expected_tokens: defaultdict
            A dictionary to store expected tokens for end activities
        end_target_tokens: defaultdict
            A dictionary to store target tokens for end activities

        Returns
        -------
        OCMarking or None
            The updated marking after moving tokens for the end activity
            Or None if the required tokens are not available
        """
        for (succ_id, ot_id), objects in produced_objects.items():
            end_act = id_to_activity[succ_id]
            if end_act not in end_activities:
                continue

            # Expected tokens in the marking
            expected_tokens = OCMarking(
                {arc_places[(act, id_to_object_type[ot_id], end_act)]: Counter(objects)}
            )

            # Target tokens in the end activity's output place
            target_tokens = OCMarking({end_output_places[end_act]: Counter(objects)})
            
            # Perform the binding without knowing if it is valid
            marking -= expected_tokens
            marking += target_tokens

            # Keep track to later check if all end bindings together were valid
            end_expected_tokens[end_act] += expected_tokens
            end_target_tokens[end_act] += target_tokens

        return marking

    @classmethod
    def _is_submarking(cls, expected_tokens: OCMarking, marking: OCMarking) -> bool:
        """
        Check if the marking contains the expected tokens.

        Parameters
        ----------
        expected_tokens: OCMarking
            The expected tokens to be present in the marking
        marking: OCMarking
            The current marking of the OCPN

        Returns
        -------
        bool
            True if the marking contains all expected tokens, False otherwise
        """
        return all(
            obj_set <= marking[place] for place, obj_set in expected_tokens.items()
        )

    @classmethod
    def _simulate_binding(
        cls,
        marking: OCMarking,
        act: str,
        expected_tokens: OCMarking,
        target_tokens: OCMarking,
        subnets: dict,
        global_binding_place: OCPetriNet.Place,
    ) -> OCMarking:
        """
        Simulate the binding of an OCCN activity in the OCPN.
        Will check if the target_tokens marking is reachable from the expected_tokens marking
        in the subnet of ocpn that corresponds to the activity act.
        This function assumes that the expected_tokens are present in the marking.
        This should be checked before calling this function.

        Parameters
        ----------
        marking: OCMarking
            The current marking of the OCPN
        act: str
            The activity to simulate
        expected_tokens: dict
            The expected tokens in the marking before the binding.
            Does not need to contain the _binding token.
        target_tokens: dict
            The target tokens in the marking after the binding
            Does not need to contain the _binding token.
        subnets: dict
            Mapping from activity names to their respective subnets in the OCPN.
        global_binding_place: OCPetriNet.Place
            The global binding place in the OCPN, where the _binding token is added.

        Returns
        -------
        OCMarking or None
            The updated marking after simulating the binding,
            or None if the binding could not be simulated successfully
        """
        ocpn_subnet = subnets[act]

        # Add the _binding token to the markings
        expected_tokens_w_binding = expected_tokens + OCMarking(
            {global_binding_place: {"_binding": 1}}
        )
        target_tokens_w_binding = target_tokens + OCMarking(
            {global_binding_place: {"_binding": 1}}
        )

        # Check if target_tokens is reachable from expected_tokens in the subnet
        parameters = {"exists_trace": True}
        success = ocpn_extensive_playout(
            ocpn_subnet, expected_tokens_w_binding, target_tokens_w_binding, parameters
        )

        if not success:
            # We cannot reach target_tokens from expected_tokens
            return None

        # We can reach target_tokens from expected_tokens, so we can create the correct marking
        marking -= expected_tokens
        marking += target_tokens

        return marking

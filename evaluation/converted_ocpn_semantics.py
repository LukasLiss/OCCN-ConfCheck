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
            - "transition_to_act": Mapping from transitions in the OCPN to the corresponding activity in the OCCN (corresponding is the activity in which subnet the transition is part of)
            - "transition_to_succ_arc_place": Mapping from transitions in the OCPN to (successor, object type) if they produce tokens for an arc place (activity, object type, successor activity) or None otherwise.
            - "transition_to_pred_arc_place": Mapping from transitions in the OCPN to (predecessor, object type) if they consume tokens from an arc place (predecessor, object type, activity) or None otherwise.
            - "transition_type": Mapping from transitions to "img" if it is part of an input marker group, "act" if it is an activity in the OCCN, or "omg" if it is part of an output marker group.
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
        transition_to_act = {}
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
                transition_to_act,
            )
        arc_places_inverse = {
            place: (pred, ot, succ) for (pred, ot, succ), place in arc_places.items()
        }
        transition_to_pred_arc_place, transition_to_succ_arc_place = (
            cls._get_transition_to_arc_place(ocpn.transitions, arc_places_inverse)
        )

        transition_type = cls._get_transition_types(
            ocpn,
            occn.activities,
            arc_places,
            start_activities,
            end_activities,
            start_input_places,
            end_output_places,
            global_binding_place,
        )

        return {
            "start_activities": start_activities,
            "end_activities": end_activities,
            "arc_places": arc_places,
            "transition_to_act": transition_to_act,
            "transition_to_pred_arc_place": transition_to_pred_arc_place,
            "transition_to_succ_arc_place": transition_to_succ_arc_place,
            "transition_type": transition_type,
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
        transition_to_act: dict,
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
        transition_to_act: dict
            Mapping from transitions in the OCPN to the corresponding activity in the OCCN.
            As a side effect, this function computes this dict for all transitions with the given activity as value.

        Returns
        -------
        OCPetriNet
            The subnet of the OCPN that corresponds to the activity
        """
        places = set()
        transitions = set()
        arcs = set()

        source_arc_places, target_arc_places = cls._get_source_target_arc_places(
            activity,
            arc_places,
            start_activities,
            end_activities,
            start_input_places,
            end_output_places,
        )

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
                        transition_to_act[target] = activity

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
    def _get_source_target_arc_places(
        cls,
        activity,
        arc_places,
        start_activities,
        end_activities,
        start_input_places,
        end_output_places,
    ):
        """
        Returns source and target arc places for the given activity as a set.
        """
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

        return source_arc_places, target_arc_places

    @classmethod
    def _get_transition_to_arc_place(cls, transitions, arc_places_inverse):
        """
        Computes a mapping from transitions in the OCPN to (successor, object type)
        if they produce tokens for an arc place (activity, object type, successor activity)
        or None otherwise, and a mapping from transitions to (predecessor, object type)
        if they consume tokens from an arc place (predecessor, object type, activity) or None otherwise.
        A transition produces / consumes tokens for / from a maximum of 1 arc place.

        Parameters
        ----------
        transitions: list
            List of transitions in the OCPN
        arc_places_inverse: dict
            Mapping from places to (pred, ot, succ) for the arc places

        Returns
        -------
        tuple
            A tuple containing two dictionaries:
            - transition_to_pred_arc_place: Mapping from transitions to (predecessor, object type)
              if they consume tokens from an arc place (predecessor, object type, activity)
            - transition_to_succ_arc_place: Mapping from transitions to (successor, object type)
              if they produce tokens for an arc place (activity, object type, successor activity)
            If a transition does not produce or consume tokens for an arc place, the value is None
        """
        transition_to_pred_arc_place = {t: None for t in transitions}
        transition_to_succ_arc_place = {t: None for t in transitions}

        # Predecessor arc places
        for transition in transitions:
            for arc in transition.in_arcs:
                (pred, ot, _) = arc_places_inverse.get(arc.source, (None, None, None))
                if pred is not None and ot is not None:
                    transition_to_pred_arc_place[transition] = (pred, ot)
                    break

        # Successor arc places
        for transition in transitions:
            for arc in transition.out_arcs:
                (_, ot, succ) = arc_places_inverse.get(arc.target, (None, None, None))
                if ot is not None and succ is not None:
                    transition_to_succ_arc_place[transition] = (succ, ot)
                    break

        return transition_to_pred_arc_place, transition_to_succ_arc_place

    @classmethod
    def _get_transition_types(
        cls,
        ocpn,
        activities,
        arc_places,
        start_activities,
        end_activities,
        start_input_places,
        end_output_places,
        global_binding_place,
    ):
        """
        Computes a mapping from transitions to
        - "img" if it is part of an input marker group,
        - "act" if it is an activity in the OCCN, or
        - "omg" if it is part of an output marker group.

        Parameters
        ----------
        ocpn
            The object-centric Petri net
        activities
            Set of activities in the OCPN
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
        global_binding_place: OCPetrinet.Place
            The global binding place in the OCPN

        Returns
        -------
        dict
            Mapping from transitions to "img", "act", or "omg".
        """
        transition_types = dict()
        transitions = {t.name: t for t in ocpn.transitions}

        for activity in activities:
            transition_types[transitions[activity]] = "act"

            source_arc_places, target_arc_places = cls._get_source_target_arc_places(
                activity,
                arc_places,
                start_activities,
                end_activities,
                start_input_places,
                end_output_places,
            )

            # BFS from source arc places to the activity to get all img transitions
            to_visit = set(source_arc_places)
            visited = set()
            visited.update(to_visit)
            # we don't go beyond the activity
            visited.add(transitions[activity])

            while to_visit:
                current = to_visit.pop()

                for arc in current.out_arcs:
                    target = arc.target
                    if target not in visited:
                        if isinstance(target, OCPetriNet.Transition):
                            transition_types[target] = "img"
                        to_visit.add(target)
                        visited.add(target)

            # BFS from activity to its target arc places to get all omg transitions
            to_visit = set([transitions[activity]])
            visited = set()
            visited.update(to_visit)
            # we don't go beyond the target arc places
            visited.update(target_arc_places)
            # we do not go beyond the global binding place
            visited.add(global_binding_place)

            while to_visit:
                current = to_visit.pop()

                for arc in current.out_arcs:
                    target = arc.target
                    if target not in visited:
                        if isinstance(target, OCPetriNet.Transition):
                            transition_types[target] = "omg"
                        to_visit.add(target)
                        visited.add(target)

        return transition_types

    @classmethod
    def replay_occn_sequence(
        cls,
        sequence,
        initial_marking: OCMarking,
        final_marking: OCMarking,
        id_to_activity,
        id_to_object_type,
        memo_reachable: set,
        memo_unreachable: set,
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
        memo_reachable: dict
            A dict to memoize bindings that could be simulated successfully.
        memo_unreachable: dict
            A dict to memoize bindings that could not be simulated successfully.

        Returns
        -------
        bool
            True if the sequence was successfully replayed, False otherwise
        """
        start_activities = precomputed["start_activities"]
        end_activities = precomputed["end_activities"]
        arc_places = precomputed["arc_places"]
        subnets = precomputed["subnet"]
        global_binding_place = precomputed["global_binding_place"]

        # Start in empty marking
        # We keep track of all tokens we assumed to be produced by the start
        # activities and check at the end if these tokens are reachable
        # from the given initial marking
        marking = OCMarking()

        # Kepp track of all the tokens we need from start activities
        # to check at the end if we can obtain these with the initial marking
        start_target_tokens = defaultdict(OCMarking)

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

            # Produce the required tokens we need from start activities
            marking = cls._bind_start_activities(
                marking,
                act,
                start_activities,
                consumed_objects,
                id_to_activity,
                id_to_object_type,
                arc_places,
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
                memo_reachable,
                memo_unreachable,
            )
            if marking is None:
                return False

        # Check if all the start activity tokens we created were valid
        if not cls._start_activity_moves_valid(
            start_target_tokens,
            initial_marking,
            subnets,
            global_binding_place,
            memo_reachable,
            memo_unreachable
        ):
            return False

        # If the sequence is replayable, the marking now only contains tokens
        # in arc places towards end activities
        # Check if we can reach a marking with tokens only in final places
        success = cls._final_marking_reachable(
            marking, final_marking, subnets, global_binding_place
        )
        return success

    @classmethod
    def _start_activity_moves_valid(
        cls,
        start_target_tokens: dict,
        initial_marking: OCMarking,
        subnets: dict,
        global_binding_place: OCPetriNet.Place,
        memo_reachable: set,
        memo_unreachable: set,
    ):
        """
        Checks if the tokens assumed to be produced by the start activities
        are reachable from the initial marking.
        This is checked individually per object type.

        Parameters
        ----------
        start_target_tokens: defaultdict
            A dictionary containing the tokens assumed to be produced by the start activities
            in the form {start_act: OCMarking}
            connecting the start activity with a successor.
        initial_marking: OCMarking
            The initial marking to check for
        subnets: dict
            Mapping from activity names to their respective subnets in the OCPN
        global_binding_place: OCPetriNet.Place
            The global binding place in the OCPN.
        memo_reachable: dict
            A dict to memoize bindings that could be simulated successfully.
        memo_unreachable: dict
            A dict to memoize bindings that could not be simulated successfully.

        Returns
        -------
        bool
            True if all start activity moves were valid, False otherwise
        """
        # check for every ot if these tokens are reachable from the initial marking
        for start_act, target_tokens in start_target_tokens.items():
            ot = start_act[6:]
            # expected tokens are the initial marking tokens for this ot
            expected_tokens = OCMarking(
                {
                    p: counter
                    for p, counter in initial_marking.items()
                    if p.object_type == ot
                }
            )

            if bool(expected_tokens.places) != bool(target_tokens.places):
                return False

            # Check if we can reach the target tokens from the expected tokens
            if not cls._simulate_binding(
                initial_marking,
                start_act,
                expected_tokens,
                target_tokens,
                subnets,
                global_binding_place,
                memo_reachable,
                memo_unreachable
            ):
                return False

        return True

    @classmethod
    def _bind_start_activities(
        cls,
        marking: OCMarking,
        act: str,
        start_activities: set,
        consumed_objects: dict,
        id_to_activity: dict,
        id_to_object_type: dict,
        arc_places: dict,
        start_target_tokens: defaultdict,
    ):
        """
        For all predecessors in consumed_objects that are start activities,
        produce the required tokens for the arc place towards the activity act.
        Does not check if these moves are valid given the initial marking.
        Stores all moves performed in start_target_tokens
        to allow for a later check once all start activities have been processed.

        Parameters
        ----------
        marking: OCMarking
            The current marking of the OCPN
        act: str
            The activity to move the token towards
        start_activities: set
            Set of start activities in the OCCN
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
    def _submarkings_per_ot(cls, marking: OCMarking) -> dict:
        """
        Returns a dictionary with submarkings of the given marking
        for each object type.

        Parameters
        ----------
        marking: OCMarking
            The marking to get the submarkings for

        Returns
        -------
        dict
            A dictionary with object types as keys and their respective submarkings as values
        """
        submarkings = defaultdict(OCMarking)
        for place, objects in marking.items():
            submarkings[place.object_type] += OCMarking({place: objects})

        return dict(submarkings)

    @classmethod
    def _simulate_binding(
        cls,
        marking: OCMarking,
        act: str,
        expected_tokens: OCMarking,
        target_tokens: OCMarking,
        subnets: dict,
        global_binding_place: OCPetriNet.Place,
        memo_reachable: set,
        memo_unreachable: set,
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
        memo_reachable: dict
            A dict to memoize bindings that could be simulated successfully.
        memo_unreachable: dict
            A dict to memoize bindings that could not be simulated successfully.

        Returns
        -------
        OCMarking or None
            The updated marking after simulating the binding,
            or None if the binding could not be simulated successfully
        """
        ocpn_subnet = subnets[act]

        # Add the _binding token to the markings
        expected_tokens_w_binding = cls._add_binding_token(
            expected_tokens, global_binding_place
        )
        target_tokens_w_binding = cls._add_binding_token(
            target_tokens, global_binding_place
        )

        # Check if target_tokens is reachable from expected_tokens in the subnet
        if (act, expected_tokens_w_binding, target_tokens_w_binding) in memo_reachable:
            # we know the marking is reachable
            pass
        elif (
            act,
            expected_tokens_w_binding,
            target_tokens_w_binding,
        ) in memo_unreachable:
            # we know the marking is not reachable
            return None
        else:
            # check if the marking is reachable
            parameters = {"exists_trace": True}
            success = ocpn_extensive_playout(
                ocpn_subnet,
                expected_tokens_w_binding,
                target_tokens_w_binding,
                parameters,
            )

            if success:
                memo_reachable[(act, expected_tokens_w_binding, target_tokens_w_binding)] = True
            else:
                # We cannot reach target_tokens from expected_tokens
                memo_unreachable[(act, expected_tokens_w_binding, target_tokens_w_binding)] = True
                return None

        # We can reach target_tokens from expected_tokens, so we can create the correct marking
        marking -= expected_tokens
        marking += target_tokens

        return marking

    @classmethod
    def _final_marking_reachable(
        cls,
        marking: OCMarking,
        final_marking: OCMarking,
        subnets: dict,
        global_binding_place: OCPetriNet.Place,
    ) -> bool:
        """
        Check if we can reach a final marking from the current marking by only
        firing transitions corresponding to end activities.
        A marking is considered final if it only contains objects in the places
        that are part of the given `final_marking`, and all other places are empty.

        Parameters
        ----------
        marking: OCMarking
            The marking of the OCPN to check
        final_marking: OCMarking
            The final marking of the OCPN
        subnets: dict
            Mapping from activity names to their respective subnets in the OCPN
        global_binding_place: OCPetriNet.Place
            The global binding place in the OCPN

        Returns
        -------
        bool
            True if a final marking is reachable, False otherwise
        """
        # Split the marking per object type
        marking_per_ot = cls._submarkings_per_ot(marking)

        # Check for every ot if we can reach a final marking using its end activity
        for ot, submarking in marking_per_ot.items():
            # Get subnet of end activity
            end_act = "END_" + ot
            subnet = subnets[end_act]

            # assert all places are in the subnet
            if not submarking.places <= subnet.places:
                return False

            # Check if we can reach a final marking using the subnet of the end activity
            parameters = {"exists_trace": True, "is_final_func": _is_final_leq}
            expected_tokens_w_binding = cls._add_binding_token(
                submarking, global_binding_place
            )
            target_tokens_w_binding = cls._add_binding_token(
                final_marking, global_binding_place
            )
            success = ocpn_extensive_playout(
                subnet, expected_tokens_w_binding, target_tokens_w_binding, parameters
            )

            if not success:
                return False

        return True

    @classmethod
    def _add_binding_token(
        cls, marking: OCMarking, global_binding_place: OCPetriNet.Place
    ) -> OCMarking:
        """
        Adds a token to the global binding place

        Parameters
        ----------
        marking: OCMarking
            The marking to add the token to
        global_binding_place: OCPetriNet.Place
            The global binding place

        Returns
        OCMarking
        -------
            The new marking
        """
        return marking + OCMarking({global_binding_place: {"_binding": 1}})

    @classmethod
    def get_original_occn_trace(
        cls, trace, idx_to_transition, id_to_obj_type, precomputed
    ):
        """
        Converts a trace from the converted OCPN to the corresponding trace for the original OCCN.

        Parameters
        ----------
        occn : OCCausalNet
            The OCCausalNet object to replay the traces on.
        trace : list of tuples
            The trace to replay
        idx_to_transition : dict
            A mapping from transition indices to transition objects in the OCPN.
        id_to_obj_type : dict
            A mapping from object IDs to their respective object types.
        precomputed : dict
            Precomputed parameters for the replay.

        Returns
        -------
        tuple
            A tuple representing the OCCN sequence, where each element is a tuple of the form
            (activity, consumed_objects, produced_objects).
        """
        transition_to_act = precomputed["transition_to_act"]
        transition_to_pred_arc_place = precomputed["transition_to_pred_arc_place"]
        transition_to_succ_arc_place = precomputed["transition_to_succ_arc_place"]
        transition_type = precomputed["transition_type"]

        # the trace has a block-structure where all bindings of transitions in one block
        # correspond to the same activity

        occn_sequence = []
        # Properties of current block
        first_transition = idx_to_transition[trace[0][0]]
        block_activity = transition_to_act[first_transition]
        last_type = transition_type[first_transition]
        block_consumed = defaultdict(lambda: defaultdict(set))
        block_produced = defaultdict(lambda: defaultdict(set))

        for event in trace:
            transition = idx_to_transition[event[0]]
            t_type = transition_type[transition]
            activity = transition_to_act[transition]

            # Check if we started a new block
            if (
                activity != block_activity
                or (last_type == "omg" and t_type == "act")
                or (last_type == "omg" and t_type == "img")
                or (last_type == "act" and t_type == "img")
            ):
                # Add the previous block to the OCCN sequence
                cls._add_to_occn_sequence(
                    block_activity, block_consumed, block_produced, occn_sequence
                )

                # Reset for the new block
                block_activity = activity
                block_consumed = defaultdict(lambda: defaultdict(set))
                block_produced = defaultdict(lambda: defaultdict(set))

            last_type = t_type

            # we are interested in gathering the objects consumed and produced
            # only if the transition consumes or produces objects from / for arc places
            if transition_to_pred_arc_place[transition]:
                pred, ot = transition_to_pred_arc_place[transition]
                objects = event[1]
                for object_id in objects:
                    object_type = id_to_obj_type[object_id]
                    if ot == object_type:  # omit the binding object type
                        block_consumed[pred][ot].add(object_id)

            if transition_to_succ_arc_place[transition]:
                succ, ot = transition_to_succ_arc_place[transition]
                objects = event[1]
                for object_id in objects:
                    object_type = id_to_obj_type[object_id]
                    if ot == object_type:  # omit the binding object type
                        block_produced[succ][ot].add(object_id)

        # Add last block to the OCCN sequence
        cls._add_to_occn_sequence(
            block_activity, block_consumed, block_produced, occn_sequence
        )
        # Convert to tuple
        return tuple(occn_sequence)

    @classmethod
    def _add_to_occn_sequence(
        cls, block_activity, block_consumed, block_produced, occn_sequence
    ):
        """
        Adds a block to the OCCN sequence.

        Parameters
        ----------
        block_activity: str
            The activity of the block
        block_consumed: dict
            The consumed objects in the block
        block_produced: dict
            The produced objects in the block
        occn_sequence: list
            The OCCN sequence to add the block to

        Returns
        -------
        None
        """
        if not block_consumed:
            block_consumed = None
        if not block_produced:
            block_produced = None
        if not block_consumed and not block_produced:
            # If both consumed and produced are empty, we skip this block
            # this happens when just binding tokens were moved
            return

        occn_sequence.append(
            (
                block_activity,
                block_consumed,
                block_produced,
            )
        )


def _is_final_leq(marking: OCMarking, final_marking: OCMarking) -> bool:
    """
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

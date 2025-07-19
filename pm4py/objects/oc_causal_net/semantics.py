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

from collections import Counter, defaultdict
from typing import Any, Generic, Set, TypeVar, Union
from copy import deepcopy
from pm4py.objects.oc_causal_net.obj import OCCausalNet


N = TypeVar("N", bound=OCCausalNet)
M = TypeVar("M", bound=OCCausalNet.Marker)
MG = TypeVar("MG", bound=OCCausalNet.MarkerGroup)


class OCCausalNetState(Generic[N], defaultdict):
    """
    The state of an object-centric causal net is a mapping from activities act to
    multisets of outstanding obligations (act2, object_id, object_type) from act2 to act.

    ```
    state = OCCausalNetState({act: Counter([(act2, object_id, object_type)])})
    ```
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the OCCausalNetState, querying unspecified activities defaults to an empty multiset."""
        super().__init__(Counter)
        data_args = args
        if args and args[0] is Counter:
            data_args = args[1:]
        initial_data = dict(*data_args, **kwargs)
        for act, obligations in initial_data.items():
            self[act] = Counter(obligations)

    def __hash__(self):
        return frozenset(
            (act, frozenset(counter.items()))
            for act, counter in self.items()
            if counter
        ).__hash__()

    def __eq__(self, other):
        if not isinstance(other, OCCausalNetState):
            return False
        return all(
            self.get(a, Counter()) == other.get(a, Counter())
            for a in set(self.keys()) | set(other.keys())
        )

    def __le__(self, other):
        for a, self_counter in self.items():
            other_counter = other.get(a, Counter())
            # Every obligation count in self must be less than or equal to the count in other.
            if not all(
                other_counter.get(pred, 0) >= count
                for pred, count in self_counter.items()
            ):
                return False
        return True

    def __add__(self, other):
        result = OCCausalNetState()
        for a, self_counter in self.items():
            result[a] += self_counter
        for a, other_counter in other.items():
            result[a] += other_counter
        return result

    def __sub__(self, other):
        result = OCCausalNetState()
        for a, self_counter in self.items():
            diff = self_counter - other.get(a, Counter())
            if diff != Counter():
                result[a] = diff
        return result

    def __repr__(self):
        # e.g.  [(a, o1[order], a'), ...]
        sorted_entries = sorted(self.items(), key=lambda item: item[0])
        obligations = [
            f"({a}, {obj_id}[{ot}], {ot}):{count}"
            for (a,obl) in sorted_entries
            for ((a_prime, obj_id, ot), count) in obl
        ]
        return f'[{", ".join(obligations) if obligations else ""}]'

    def __str__(self):
        return self.__repr__()
    
    def __deepcopy__(self, memodict={}):
        new_state = OCCausalNetState()
        memodict[id(self)] = new_state
        for act, obligations in self.items():
            act_copy = (
                memodict[id(act)]
                if id(act) in memodict
                else deepcopy(act, memodict)
            )
            counter_copy = (
                memodict[id(obligations)]
                if id(obligations) in memodict
                else deepcopy(obligations, memodict)
            )
            new_state[act_copy] = counter_copy
        return new_state

    @property
    def activities(self) -> Set:
        """
        Set of activities with outstanding obligations.
        """
        return set(act for act in self.keys() if self[act])

class OCCausalNetSemantics(Generic[N]):
    """
    Class for the semantics of object-centric causal nets
    """

    @classmethod
    def is_enabled(cls, occn: N, act: str, state: OCCausalNetState) -> bool:
        """
        Checks whether a given activity is enabled in a given object-centric
        casal net and state.
        An activity is enabled if there exists an input marker group that can be
        bound.
        
        Parameters
        ----------
        occn
            Object-centric causal net
        act
            Activity to check
        state
            State of the OCCN
            
        Returns
        -------
        bool
            true if enabled, false otherwise
        """
        imgs = occn.input_marker_groups[act]
        
        # check each img
        for img in imgs:
            # markers that allow for consumption of 0 obligations do not need to be enabled
            # at least one marker of the img needs to be enabled
            one_marker_enabled = False
            for marker in img:
                min_count = marker.min_count
                if state[act].get((marker.related_activity, marker.object_type), -1) >= min_count:
                    one_marker_enabled = True
                elif min_count != 0:
                    # marker is not enabled, move on to next img
                    one_marker_enabled = False
                    break
            if one_marker_enabled:
                return True
        return False
    
    @classmethod
    def _find_matching_marker_group(cls, obligations: dict, marker_groups: list) -> Union[MG, None]:
        """
        Finda a matching marker group that is able to consume/produce the given obligations.
        
        Parameters
        ----------
        obligations : dict
            Obligations to consume, mapping related activities to a dict mapping
            object types to a set of object ids
        marker_groups : list
            List of marker groups to check
            
        Returns
        -------
        Union[MG, None]
            A matching marker group if found, None otherwise.
        """
        # Calculate object counts from the obligations
        obj_counts = {
            related_act: {ot: len(obligations[related_act][ot]) for ot in obligations[related_act]}
            for related_act in obligations
        }
        
        # check each group
        for mg in marker_groups:
            mg_dict = mg.dict_representation
            
            # 1: check that count matches (= is within cardinality bounds)
            counts_match = all(
                mg_dict[related_act][ot][1] >= obj_counts[related_act][ot] >= mg_dict[related_act][ot][0]
                for related_act in obj_counts
                for ot in obj_counts[related_act]
            )
            if not counts_match:
                continue
            
            # 2: check key constraints
            constraints_violated = any(
                obligations.get(rel_act_1, {}).get(ot, set()).intersection(
                    obligations.get(rel_act_2, {}).get(ot, set())
                )
                for (rel_act_1, ot, rel_act_2) in mg.key_constraints
            )
            if constraints_violated:
                continue
            
            # found matching group
            return mg
        
        return None
    
    @classmethod
    def is_binding_enabled(cls, net: N, act: str, cons: dict[str, dict[str, Set]], prod: dict[str, dict[str, Set]], state: OCCausalNetState) -> Union[tuple[MG, MG], None]:
        """
        Checks whether the given binding is enabled in the object-centric causal net.
        A binding is enabled if the activity has input and output marker groupos that 
        match the given objects and the state contains all necessary obligations.
        
        
        Parameters
        ----------
        net : N
            The object-centric causal net
        act : str
            The activity to bind
        cons : dict[str, dict[str, Set]]
            The obligations to consume, mapping predecessor activities to a dict mapping
            object types to a set of object ids
        prod : dict[str, dict[str, Set]]
            The obligations to produce, mapping successor activities to a dict mapping
            object types to a set of object ids
        state : OCCausalNetState
            The current state of the OCCN
            
        Returns
        -------
        Union[tuple[MG, MG], None]:
            The input and output marker groups enabling the binding if it is enabled, None otherwise.
        """
        # 1: check that all consumed obligations are present in the state
        if cons:
            if any(
                state[act].get((pred, obj_id, ot), 0) <= 0
                for pred in cons.keys()
                for ot in cons[pred].keys()
                for obj_id in cons[pred][ot]
            ):
                return None
        else:
            if not prod:
                # we need to either consume or produce obligations
                return None

        # 2: Find a matching input marker group
        if act.startswith("START_"):
            if cons:
                return None
            # For START activities, we do not consume obligations, cons has to be empty
            matched_img = None
        else:
            matched_img = cls._find_matching_marker_group(cons, net.input_marker_groups[act])
            if matched_img is None:
                return None

        # 3: Find a matching output marker group
        if act.startswith("END_"):
            if prod:
                return None
            # For START activities, we do not consume obligations, prod has to be empty
            matched_omg = None
        else:
            matched_omg = cls._find_matching_marker_group(prod, net.output_marker_groups[act])
            if matched_omg is None:
                return None

        return (matched_img, matched_omg)

                    
    
    @classmethod
    def bind_activity(cls, net: N, act: str, cons: dict[str, dict[str, Set]], prod: dict[str, dict[str, Set]], state: OCCausalNetState) -> OCCausalNetState:
        """
        Binds an activity in the object-centric causal net.
        For performance reasons, this method does not check whether the binding
        is valid given the current state. If necessary, the caller should
        ensure this, e.g., using the `is_binding_enabled` method.
        
        Parameters
        ----------
        net : N
            The object-centric causal net
        act : str
            The activity to bind
        cons : dict[str, dict[str, Set]]
            The obligations to consume, mapping predecessor activities to a dict mapping
            object types to a set of object ids
        prod : dict[str, dict[str, Set]]
            The obligations to produce, mapping successor activities to a dict mapping
            object types to a set of object ids
        state : OCCausalNetState
            The current state of the OCCN
            
        Returns
        -------
        OCCausalNetState
            The new state after binding the activity
        """
        # consume obligations
        if cons:
            consume = OCCausalNetState(
                {act:
                    Counter([(pred, obj_id, ot) for pred in cons for ot in cons[pred] for obj_id in cons[pred][ot]])
                    }
            )
            state -= consume
        
        # produce obligations
        if prod:
            produce = OCCausalNetState(
                {succ:
                    Counter([(act, obj_id, ot) for ot in prod[succ] for obj_id in prod[succ][ot]])
                    for succ in prod}
            )
            state += produce
        
        return state
    
    @classmethod
    def replay(cls, occn: N, sequence: tuple) -> bool:
        """
        Replays a sequence of bindings on the object-centric causal net.
        
        Parameters
        ----------
        occn : N
            The object-centric causal net to replay on.
        sequence : tuple
            A sequence of bindings, where each binding is a tuple of (activity_name, consumed_obligations, produced_obligations).
            consumed_obligations and produced_obligations are dictionaries mapping
            related activities to a dict mapping object types to a set of object ids.
            
        Returns
        -------
        bool
            True if the sequence can be replayed on the net, False otherwise.
        """
        # start in the empty state
        state = OCCausalNetState()
        
        # replay each binding
        for act, cons, prod in sequence:
            if not cls.is_binding_enabled(occn, act, cons, prod, state):
                return False
            
            state = cls.bind_activity(occn, act, cons, prod, state)
        
        # check if we are in the empty state
        if state.activities:
            return False
        
        return True
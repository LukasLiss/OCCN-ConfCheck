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

from collections import Counter
from copy import deepcopy
from typing import Collection, Dict, Any, Set
from pm4py.objects.petri_net.obj import PetriNet


class OCMarking(Counter):
    """An object-centric marking is a multiset of (object_id, place) pairs.

    Keys are tuples (object_id, place) and values are integer multiplicities.
    """

    def __hash__(self):
        # include counts in the hash
        return frozenset(self.items()).__hash__()

    def __eq__(self, other):
        if not isinstance(other, OCMarking):
            return False
        return all(self.get(k, 0) == other.get(k, 0) for k in set(self) | set(other))

    def __le__(self, other):
        for k, v in self.items():
            if other.get(k, 0) < v:
                return False
        return True

    def __add__(self, other):
        result = OCMarking()
        for k, v in self.items():
            result[k] = v
        for k, v in other.items():
            result[k] = result.get(k, 0) + v
        return result

    def __sub__(self, other):
        result = OCMarking()
        for k, v in self.items():
            diff = v - other.get(k, 0)
            if diff > 0:
                result[k] = diff
        return result

    def __repr__(self):
        # e.g.  ["order1@p1:2", "order2@p3:1", …]
        entries = sorted(self.items(), key=lambda item: (item[0][1].name, item[0][0]))
        return str(
            [f"{obj_id}@{place.name}:{count}" for (obj_id, place), count in entries]
        )

    def __str__(self):
        return self.__repr__()

    def __deepcopy__(self, memodict={}):
        new_marking = OCMarking()
        memodict[id(self)] = new_marking
        for (obj_id, place), count in self.items():
            place_copy = (
                memodict[id(place)]
                if id(place) in memodict
                else deepcopy(place, memodict)
            )
            new_marking[(obj_id, place_copy)] = count
        return new_marking


class OCPetriNet(object):
    class Place(PetriNet.Place):
        def __init__(
            self, name, object_type, in_arcs=None, out_arcs=None, properties=None
        ):
            """
            Constructor

            Parameters
            ------------
            name
                human-readable identifier
            object_type
                the type/color of objects this place holds
            in_arcs
                set of incoming arcs
            out_arcs
                set of outgoing arcs
            properties
                dict of additional properties
            """
            super().__init__(
                name, in_arcs=in_arcs, out_arcs=out_arcs, properties=properties
            )
            self.__object_type = object_type

        def __get_object_type(self):
            return self.__object_type

        def __repr__(self):
            return f"{self.name}[{self.object_type}]"

        def __deepcopy__(self, memodict={}):
            if id(self) in memodict:
                return memodict[id(self)]
            new_place = OCPetriNet.Place(
                self.name, self.object_type, properties=self.properties
            )
            memodict[id(self)] = new_place
            # attached arcs
            for arc in self.in_arcs:
                arc_copy = deepcopy(arc, memodict)
                new_place.in_arcs.add(arc_copy)
            for arc in self.out_arcs:
                arc_copy = deepcopy(arc, memodict)
                new_place.out_arcs.add(arc_copy)

            return new_place

        object_type = property(__get_object_type)

    class Transition(PetriNet.Transition):
        # Standard PetriNet.Transition
        pass

    class Arc(PetriNet.Arc):
        def __init__(
            self,
            source,
            target,
            object_type,
            weight=1,
            is_double=False,
            properties=None,
        ):
            """
            Constructor

            Parameters
            ------------
            source
                source place / transition
            target
                target place / transition
            weight
                weight of the arc
            is_double
                whether the arc is double (variable)
            properties
                dict of additional properties
            """
            super().__init__(source, target, weight=weight, properties=properties)
            self.__object_type = object_type
            self.__is_double = is_double

        def __get_object_type(self):
            return self.__object_type

        def __get_is_double(self):
            return self.__is_double

        def __repr__(self):
            base = super().__repr__()
            dbl = "double" if self.is_double else "single"
            return f"{base}:{self.object_type}:{dbl}"

        def __deepcopy__(self, memodict={}):
            if id(self) in memodict:
                return memodict[id(self)]
            new_source = memodict.get(id(self.source), deepcopy(self.source, memodict))
            new_target = memodict.get(id(self.target), deepcopy(self.target, memodict))
            new_arc = OCPetriNet.Arc(
                new_source,
                new_target,
                self.object_type,
                weight=self.weight,
                is_double=self.is_double,
                properties=self.properties,
            )
            memodict[id(self)] = new_arc
            # reattach
            new_source.out_arcs.add(new_arc)
            new_target.in_arcs.add(new_arc)
            return new_arc

        object_type = property(__get_object_type)
        is_double = property(__get_is_double)

    def __init__(
        self,
        name: str = None,
        places: Collection[Place] = None,
        transitions: Collection[Transition] = None,
        arcs: Collection[Arc] = None,
        initial_marking: OCMarking = None,
        final_marking: OCMarking = None,
        properties: Dict[str, Any] = None,
    ):
        """
        Constructor

        Parameters
        ------------
        name
            human-readable identifier
        places
            collection of places
        transitions
            collection of transitions
        arcs
            collection of arcs
        initial_marking
            initial marking of the net
        final_marking
            final marking of the net
        properties
            dict of additional properties
        """
        super().__init__(
            name=name,
            places=places,
            transitions=transitions,
            arcs=arcs,
            properties=properties,
        )
        self.__initial_marking = initial_marking
        self.__final_marking = final_marking

    def __get_initial_marking(self):
        return self.__initial_marking

    def __get_final_marking(self):
        return self.__final_marking

    def __deepcopy__(self, memodict={}):
        new_net = OCPetriNet(self.name)
        memodict[id(self)] = new_net
        for p in self.places:
            p_copy = OCPetriNet.Place(p.name, p.object_type, properties=p.properties)
            new_net.places.add(p_copy)
            memodict[id(p)] = p_copy
        for t in self.transitions:
            t_copy = OCPetriNet.Transition(t.name, t.label, properties=t.properties)
            new_net.transitions.add(t_copy)
            memodict[id(t)] = t_copy
        for a in self.arcs:
            src = memodict[id(a.source)]
            tgt = memodict[id(a.target)]
            a_copy = OCPetriNet.Arc(
                src,
                tgt,
                a.object_type,
                weight=a.weight,
                is_double=a.is_double,
                properties=a.properties,
            )
            src.out_arcs.add(a_copy)
            tgt.in_arcs.add(a_copy)
            new_net.arcs.add(a_copy)
            memodict[id(a)] = a_copy
        return new_net

    def __repr__(self):
        ret = ["object_types: ["]
        object_types_rep = []
        for ot in self.object_types:
            object_types_rep.append(ot)
        object_types_rep.sort()
        ret.append(" " + ", ".join(object_types_rep) + " ")
        ret.append("]\nplaces: [")
        places_rep = []
        for place in self.places:
            places_rep.append(repr(place))
        places_rep.sort()
        ret.append(" " + ", ".join(places_rep) + " ")
        ret.append("]\ntransitions: [")
        trans_rep = []
        for trans in self.transitions:
            trans_rep.append(repr(trans))
        trans_rep.sort()
        ret.append(" " + ", ".join(trans_rep) + " ")
        ret.append("]\narcs: [")
        arcs_rep = []
        for arc in self.arcs:
            arcs_rep.append(repr(arc))
        arcs_rep.sort()
        ret.append(" " + ", ".join(arcs_rep) + " ")
        ret.append("]\ninitial_marking: [")
        initial_marking_rep = [repr(self.initial_marking)]
        ret.append(" " + ", ".join(initial_marking_rep) + " ")
        ret.append("]\nfinal_marking: [")
        final_marking_rep = [repr(self.final_marking)]
        ret.append(" " + ", ".join(final_marking_rep) + " ")
        ret.append("]")
        return "".join(ret)
    
    def __str__(self):
        return self.__repr__()

    initial_marking = property(__get_initial_marking)
    final_marking = property(__get_final_marking)

    @property
    def object_types(self) -> Set[str]:
        """
        Returns the set of all object types (colors) used in this net.

        Returns
        ------------
        Set[str]
            Set of object types (colors) used in this net.
        """
        return {p.object_type for p in self.places}

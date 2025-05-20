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
from pm4py.objects.oc_causal_net.utils.filters import filter4
from typing import Tuple, List, Dict


class OCCausalNet(object):
    """
    Object-Centric Causal Net capturing dependency graph and token bindings.
    """

    class Obligation(object):
        """
        Represents an obligation that has to be fulfilled by an activity.
        Also referred to as 'marker' in literature.
        """

        def __init__(
            self, related_activity, object_type, count_range: Tuple, marker_key: int
        ):
            """
            Constructor

            Parameters
            ----------
            related_activity : str
                Activity that has to fulfill the obligation (predecessor or successor)
            object_type : str
                Type of object that is bound to the obligation
            count_range : Tuple
                Min and max number of obligations consumable ('cardinalities')
            marker_key : int
                Key of the marker
            """
            self.__related_activity = related_activity
            self.__object_type = object_type
            self.__count_range = count_range
            self.__marker_key = marker_key

        def __repr__(self):
            return f"(a={self.related_activity}, ot={self.object_type}, c={self.count_range}, k={self.marker_key})"

        def __str__(self):
            return self.__repr__()

        def __get_related_activity(self):
            return self.__related_activity

        def __get_object_type(self):
            return self.__object_type

        def __get_count_range(self):
            return self.__count_range

        def __get_min_count(self):
            return self.__count_range[0]

        def __get_max_count(self):
            return self.__count_range[1]

        def __get_marker_key(self):
            return self.__marker_key

        def __eq__(self, other):
            if isinstance(other, OCCausalNet.Obligation):
                return (
                    self.related_activity == other.related_activity
                    and self.object_type == other.object_type
                    and self.count_range == other.count_range
                    and self.marker_key == other.marker_key
                )
            return False

        related_activity = property(__get_related_activity)
        object_type = property(__get_object_type)
        count_range = property(__get_count_range)
        min_count = property(__get_min_count)
        max_count = property(__get_max_count)
        marker_key = property(__get_marker_key)

    class ObligationSet(object):
        """
        Represents a set of obligations.
        Also referred to as 'marker group' in literature.
        """

        def __init__(
            self, obligations: List["OCCausalNet.Obligation"], support_count: int = 0
        ):
            """
            Constructor

            Parameters
            ----------
            obligations : List[OCCausalNet.Obligation]
                List of obligations that comprise the set
            support_count : int
                Frequency of this obligation set in the event log. May be used to filter infrequent obligation sets.
                Default is 0.
            """
            self.__obligations = obligations
            self.__support_count = support_count

        def __repr__(self):
            return f"({self.obligations}, count={self.support_count})"

        def __str__(self):
            return self.__repr__()

        def __get_obligations(self):
            return self.__obligations

        def __get_support_count(self):
            return self.__support_count

        obligations = property(__get_obligations)
        support_count = property(__get_support_count)

    def __init__(
        self,
        dependency_graph: nx.MultiDiGraph,
        output_bindings: Dict[str, List["OCCausalNet.ObligationSet"]],
        input_bindings: Dict[str, List["OCCausalNet.ObligationSet"]],
        activity_count: Dict[str, int] = None,
        relative_occurrence_threshold: float = 0,
    ):
        """
        Constructor

        Parameters
        ----------
        dependency_graph : nx.MultiDiGraph
            Object-centric dependency graph
        output_bindings : Dict[str, List[OCCausalNet.ObligationSet]]
            Output binding sets of the activities
        input_bindings : Dict[str, List[OCCausalNet.ObligationSet]]
            Input binding sets of the activities
        activity_count : Dict[str, int]
            Activity counts in the event log for filtering of infrequent obligation sets.
        relative_occurrence_threshold : float
            Relative threshold for filtering infrequent obligation sets. Range is [0,1].
            Default is 0, meaning no filtering.
        """
        self.__dependency_graph = dependency_graph
        self.__activities = list(dependency_graph._node.keys())
        self.__edges = dependency_graph._succ
        self.__relative_occurrence_threshold = relative_occurrence_threshold
        self.__input_bindings, self.__output_bindings = filter4(
            input_bindings,
            output_bindings,
            self.__relative_occurrence_threshold,
            (
                activity_count
                if activity_count is not None
                else {act: 0 for act in self.activities}
            ),
        )
        self.__object_types = {
            o.object_type
            for binds in self.__input_bindings.values()
            for bs in binds
            for o in bs.obligations
        }
        self.__activity_count = activity_count

    def __repr__(self):
        ret = f"Dependency graph: {self.dependency_graph}\n"
        for act in self.activities:
            ret += f"Input bindings[{act}]: {self.input_bindings[act]}\n"
            ret += f"Output bindings[{act}]: {self.output_bindings[act]}\n"
        return ret

    def __str__(self):
        return self.__repr__()

    def __get_dependency_graph(self):
        return self.__dependency_graph

    def __get_activities(self):
        return self.__activities

    def __get_edges(self):
        return self.__edges

    def __get_input_bindings(self):
        return self.__input_bindings

    def __get_output_bindings(self):
        return self.__output_bindings

    def __get_object_types(self):
        return self.__object_types

    def __get_activity_count(self):
        return self.__activity_count

    def __get_relative_occurrence_threshold(self):
        return self.__relative_occurrence_threshold

    dependency_graph = property(__get_dependency_graph)
    activities = property(__get_activities)
    edges = property(__get_edges)
    input_bindings = property(__get_input_bindings)
    output_bindings = property(__get_output_bindings)
    object_types = property(__get_object_types)
    activity_count = property(__get_activity_count)
    relative_occurrence_threshold = property(__get_relative_occurrence_threshold)

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


def filter4(input_bindings, output_bindings, threshold, activity_count):
    """
    Filters input_bindings and output_bindings by relative support, then
    recursively keeps only those ObligationSets that remain connected.

    Parameters
    ----------
    input_bindings : Dict[str, List[OCCausalNet.ObligationSet]]
        Input binding sets of the activities
    output_bindings : Dict[str, List[OCCausalNet.ObligationSet]]
        Output binding sets of the activities
    threshold : float
        Minimum relative support = support_count / activity_count[activity]
    activity_count : Dict[str,int]
        Absolute frequency of each activity in the event log.

    Returns
    -------
    Tuple[
        Dict[str, List[OCCausalNet.ObligationSet]],
        Dict[str, List[OCCausalNet.ObligationSet]]
    ]
        (filtered_input_bindings, filtered_output_bindings)
    """

    def filterByTreshold(binding_list, activity):
        """
        Filters a list of ObligationSets by relative support.

        Parameters
        ----------
        binding_list : List[OCCausalNet.ObligationSet]
            The obligation sets to filter.
        activity : str
            Activity name whose frequency is used for relative support.

        Returns
        -------
        List[OCCausalNet.ObligationSet]
            Those sets whose support_count / activity_count[activity] > threshold.
        """
        filteredBindings = [
            obl_set
            for obl_set in binding_list
            if obl_set.support_count / activity_count[activity] > threshold
        ]
        return filteredBindings

    def getMostFrequent(binding_list):
        """
        Returns the most frequent ObligationSet in the list.

        Parameters
        ----------
        binding_list : List[OCCausalNet.ObligationSet]
            List of obligation sets to examine.

        Returns
        -------
        OCCausalNet.ObligationSet
            The one with the highest support_count.
        """
        mostFrequentBinding = binding_list[
            [obl_set.support_count for obl_set in binding_list].index(
                max([obl_set.support_count for obl_set in binding_list])
            )
        ]
        return mostFrequentBinding

    def getSubsequentInputBidnings(mostFrequentBinding, activity):
        """
        For every obligation in *mostFrequentBinding* (which belongs to an
        **output** binding of *activity*) look up the corresponding input
        bindings of the obligation's successor activity.
        Keeps only the most frequent ones and adds them to the
        *filtered_input_bindings* structure.

        Parameters
        ----------
        mostFrequentBinding : OCCausalNet.ObligationSet
        activity : str
        """
        for obligation in mostFrequentBinding.obligations:
            succ_activity = obligation.related_activity
            if succ_activity in input_bindings.keys():
                possibleInputBindings = [
                    x
                    for x in input_bindings[succ_activity]
                    if (activity, obligation.object_type)
                    in [(y.related_activity, y.object_type) for y in x.obligations]
                ]
                mostFrequentBinding = getMostFrequent(possibleInputBindings)
                addToFilteredInputBindings(mostFrequentBinding, succ_activity)

    def addToFilteredOutputBindings(mostFrequentBinding, activity):
        """
        Inserts *mostFrequentBinding* into *filtered_output_bindings* and
        triggers the recursive traversal to the input side.

        Parameters
        ----------
        mostFrequentBinding : OCCausalNet.ObligationSet
        activity : str
        """
        if mostFrequentBinding not in filtered_output_bindings[activity]:
            filtered_output_bindings[activity].append(mostFrequentBinding)
            getSubsequentInputBidnings(mostFrequentBinding, activity)

    def getSubsequentOutputBidnings(mostFrequentBinding, activity):
        """
        For every obligation in *mostFrequentBinding* (which belongs to an
        **input** binding of *activity*) look up the corresponding output
        bindings of the obligation's predecessor activity.
        Keeps only the most frequent ones and adds them to the
        *filtered_output_bindings* structure.

        Parameters
        ----------
        mostFrequentBinding : OCCausalNet.ObligationSet
        activity : str
        """
        for obligation in mostFrequentBinding.obligations:
            pred_activity = obligation.related_activity
            if pred_activity in output_bindings.keys():
                possibleOutputBindings = [
                    x
                    for x in output_bindings[pred_activity]
                    if (activity, obligation.object_type)
                    in [(y.related_activity, y.object_type) for y in x.obligations]
                ]
                mostFrequentBinding = getMostFrequent(possibleOutputBindings)
                addToFilteredOutputBindings(mostFrequentBinding, pred_activity)

    def addToFilteredInputBindings(mostFrequentBinding, activity):
        """
        Inserts *mostFrequentBinding* into *filtered_input_bindings* and
        triggers the recursive traversal to the output side.

        Parameters
        ----------
        mostFrequentBinding : OCCausalNet.ObligationSet
        activity : str
        """
        if mostFrequentBinding not in filtered_input_bindings[activity]:
            filtered_input_bindings[activity].append(mostFrequentBinding)
            getSubsequentOutputBidnings(mostFrequentBinding, activity)

    filtered_output_bindings = {act: [] for act in output_bindings.keys()}
    filtered_input_bindings = {act: [] for act in input_bindings.keys()}

    for act in filtered_output_bindings.keys():
        filteredBindings = filterByTreshold(output_bindings[act], act)
        for binding in filteredBindings:
            addToFilteredOutputBindings(binding, act)

    for act in filtered_input_bindings.keys():
        filteredBindings = filterByTreshold(input_bindings[act], act)
        for binding in filteredBindings:
            addToFilteredInputBindings(binding, act)

    return filtered_input_bindings, filtered_output_bindings

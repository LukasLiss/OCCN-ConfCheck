from collections import defaultdict
from typing import Set, TypeVar
from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.oc_causal_net.semantics import OCCausalNetSemantics, OCCausalNetState
from pm4py.objects.oc_causal_net.utils.occn_utils import pre_set, post_set

N = TypeVar("N", bound=OCCausalNet)
M = TypeVar("M", bound=OCCausalNet.Marker)
MG = TypeVar("MG", bound=OCCausalNet.MarkerGroup)


class ConvertedOCCausalNetSemantics(OCCausalNetSemantics[N]):
    """
    Class for the semantics of object-centric causal nets that were obtained
    by converting an object-centric Petri net, see pm4py.objects.ocpn.variants.to_oc_causal_net.
    """

    @classmethod
    def replay(cls, occn: N, trace: tuple) -> bool:
        """
        Replays a trace from an object-centric Petri net on the converted object-centric causal net.

        Parameters
        ----------
        occn : N
            The object-centric causal net to replay on.
        trace : tuple
            A trace from the object-centric Petri net,
            represented as a tuple of (transition_name, {object_type: set(object_ids)}) tuples.

        Returns
        -------
        bool
            True if the trace can be replayed on the net, False otherwise.
        """
        # start in the empty state
        state = OCCausalNetState()

        # get all objects per object type
        objects_per_type = defaultdict(set)
        for transition_name, objects in trace:
            for ot, obj_ids in objects.items():
                objects_per_type[ot].update(obj_ids)

        # add START activity bindings
        for ot, obj_ids in objects_per_type.items():
            act = f"START_{ot}"
            prod = {p: {ot: obj_ids} for p in post_set(occn, f"START_{ot}", ot)}
            if not OCCausalNetSemantics.is_binding_enabled(
                occn, act, None, prod, state
            ):
                return False
            # bind activity
            state = OCCausalNetSemantics.bind_activity(occn, act, None, prod, state)

        # construct artificial end bindings for the ocpn trace so the following loop
        # creates the correct end activity bindings
        end_act_tuples = [
            (f"END_{ot}", {ot: objects_per_type[ot]}) for ot in objects_per_type.keys()
        ]

        # traverse the trace
        for transition_name, objects in trace + tuple(end_act_tuples):
            # pred places of transition
            pred_places = {
                ot: pre_set(occn, transition_name, ot) for ot in objects.keys()
            }         

            # 1: bind the predecessor places (or the auxiliary activity)
            for ot in objects.keys():
                # check if the pred is an aux activity
                is_aux = False
                preds = list(pred_places[ot])
                if len(preds) == 1 and preds[0].startswith("_silent_aux_"):
                    is_aux = True
                    aux = preds[0]
                    # replace pred_places with the predecessors of the aux activity (restored later)
                    pred_places[ot] = pre_set(occn, aux, ot)
                    
                # bind all predecessor places
                for pred_place in pred_places[ot]:
                    cons = cls._get_outstanding_obligations(
                        pred_place, objects[ot], ot, state
                    )

                    # we need to bind pred_place per predecessor of pred_place
                    for pred_pred_place in cons.keys():
                        pred_pred_objects = cons[pred_pred_place][ot]

                        sub_cons = {pred_pred_place: {ot: pred_pred_objects}}
                        prod = {transition_name: {ot: pred_pred_objects}} if not is_aux else {aux: {ot: pred_pred_objects}}

                        if not OCCausalNetSemantics.is_binding_enabled(
                            occn, pred_place, sub_cons, prod, state
                        ):
                            return False
                        # bind the place
                        state = OCCausalNetSemantics.bind_activity(
                            occn, pred_place, sub_cons, prod, state
                        )
                
                # bind the aux activity with all objects
                if is_aux:
                    for obj_id in objects[ot]:
                        cons = {
                            aux_pred: {ot: {obj_id}}
                            for aux_pred in pre_set(occn, aux, ot)
                        }
                        prod = {
                            transition_name: {ot: {obj_id}}
                        }
                        if not OCCausalNetSemantics.is_binding_enabled(
                            occn, aux, cons, prod, state
                        ):
                            return False
                        # bind the auxiliary activity
                        state = OCCausalNetSemantics.bind_activity(
                            occn, aux, cons, prod, state
                        )
                    # restore pred_places
                    pred_places[ot] = {aux}
                    

            # 2: bind the transition
            cons = {
                pred_place: {ot: objects[ot]}
                for ot in objects.keys()
                for pred_place in pred_places[ot]
            }
            prod = {
                succ_place: {ot: objects[ot]}
                for ot in objects.keys()
                for succ_place in post_set(occn, transition_name, ot)
            }
            if not OCCausalNetSemantics.is_binding_enabled(
                occn, transition_name, cons, prod, state
            ):
                return False
            # bind the transition
            state = OCCausalNetSemantics.bind_activity(
                occn, transition_name, cons, prod, state
            )
            
            # 3: check if the transition has an auxiliary successor activity
            for ot in objects.keys():
                successors = post_set(occn, transition_name, ot)
                if len(successors) == 1:
                    aux_act_name = successors.pop()
                    if aux_act_name.startswith("_silent_aux_"):
                        # bind the auxiliary activity
                        for obj_id in objects[ot]:
                            cons = {
                                transition_name: {ot: {obj_id}}
                            }
                            prod = {
                                aux_successor: {ot: {obj_id}}
                                for aux_successor in post_set(occn, aux_act_name, ot)
                            }
                            if not OCCausalNetSemantics.is_binding_enabled(
                                occn, aux_act_name, cons, prod, state
                            ):
                                return False
                            # bind the auxiliary activity
                            state = OCCausalNetSemantics.bind_activity(
                                occn, aux_act_name, cons, prod, state
                            )

        # Check if we are in the empty state
        if state.activities:
            # Check if outstanding obligations are only to the end activities
            # In this case, we can consider the trace as valid as the end activities
            # only have one input marker group; this one can consume all remaining obligations
            for activity in state.activities:
                if not activity.startswith("END_"):
                    # If there is an activity that is not an end activity, the trace is invalid
                    return False
        return True

    @classmethod
    def _get_outstanding_obligations(
        cls, activity: str, object_ids: Set, object_type: str, state: OCCausalNetState
    ) -> dict[str, dict[str, Set]]:
        """
        Get the outstanding obligations in the given state for the
        specified activity, object ids, and object type.
        Will return a dictionary mapping predecessor activities to a dictionary
        mapping the specified object type to the subset of object ids from the given set
        that originate from the predecessor activity.

        Parameters
        ----------
        activity : str
            The name of the activity for which to get the obligations.
        object_ids : Set
            The set of object ids to check for obligations.
        object_type : str
            The object type to restrict the obligations to.
        state : OCCausalNetState
            The current state of the object-centric causal net.

        Returns
        -------
        dict[str, dict[str, Set]]
            A dictionary mapping predecessor activities to a dictionary
            mapping the specified object type to the subset of object ids from the given set
            that originate from the predecessor activity.
        """
        pred_act_to_obj_ids = defaultdict(lambda: defaultdict(set))

        for related_act, obj_id, ot in state[activity]:
            if ot == object_type and obj_id in object_ids:
                pred_act_to_obj_ids[related_act][ot].add(obj_id)

        # check that all object ids are accounted for
        all_objs = set.union(
            *[
                objects
                for _, obj_dict in pred_act_to_obj_ids.items()
                for _, objects in obj_dict.items()
            ]
        )
        if all_objs != object_ids:
            raise ValueError(
                "Not all object ids are present in the obligations. Object Ids: {} with object type {}; state for activity {}: {}".format(
                    object_ids, object_type, activity, state[activity]
                )
            )

        return dict(pred_act_to_obj_ids)

    @classmethod
    def get_original_ocpn_trace(cls, ocpn, sequence, id_to_activity, id_to_object_type):
        """
        Converts a binding sequence generated by a transformed OCCN to the corresponding
        trace in the original OCPN.

        Parameters
        ----------
        ocpn : object
            The original object-Centric Petri Net.
        sequence : tuple
            The sequence of the occn, as a tuple of (activity_id, consumed, produced) tuples
        id_to_activity : dict
            A mapping from activity IDs to activity names.
        id_to_object_type : dict
            A mapping from object type IDs to object type names.

        Returns
        -------
        tuple
            The corresponding trace in the original OCPN as a tuple of 
            (transition_name, {object_type: set(object_ids)}) tuples.
        """
        trace_elements = []
        ocpn_place_names = {p.name for p in ocpn.places}
        
        for (activity_id, consumed, _) in sequence:
            act = id_to_activity[activity_id]
            
            # Bindings of these activities must be omitted
            if act.startswith("START_") or act.startswith("END_") or act.startswith("_silent_aux_") or act in ocpn_place_names:
                continue
            
            # act is a transition now
            
            # Get all the objects; consumed and produced have the same objects
            obj_per_ot = defaultdict(set)
            for _, ot_to_obj in consumed:
                for ot_id, objects in ot_to_obj:
                    ot = id_to_object_type[ot_id]
                    obj_per_ot[ot].update(objects)
                    
            trace_elements.append((act, dict(obj_per_ot)))
        
        return tuple(trace_elements)
                    

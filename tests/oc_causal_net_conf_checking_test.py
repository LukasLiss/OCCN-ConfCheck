import unittest

import pandas as pd
from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net
from pm4py.algo.simulation.playout.oc_causal_net.variants import (
    extensive as playout_extensive,
)
from pm4py.algo.occn_evaluation.replay_fitness import algorithm as occn_replay_fitness
from pm4py.objects.ocel import constants


class OCCausalNetConfCheckingTest(unittest.TestCase):

    def test_playout_and_replay(self):
        # Playout all ~250 sequences with 2 objects and compute fitness with
        # the generated OCEL. Should be 1
        # This tests the replay as well as the process execution extraction
        occn = occn_ABC()

        parameters = {
            playout_extensive.Parameters.MAX_BINDINGS_PER_ACTIVITY: 3,
            playout_extensive.Parameters.RETURN_SEQUENCES: False,
            playout_extensive.Parameters.OBJECTS_UNIQUE_PER_SEQUENCE: True,
        }

        objects = {"order": {"o1", "o2"}}
        # ~250 sequences with ~500 process executions (due to 2 concurrent but unrelated objects)
        ocel = playout_extensive.apply(occn, objects, parameters)
        fitness = occn_replay_fitness.apply(ocel=ocel, occn=occn)
        self.assertGreaterEqual(fitness["no_process_executions"], 500)
        self.assertEqual(fitness["log_fitness"], 1.0)

    def test_playout_and_replay_2(self):
        # Playout all 540 sequences and compute fitness with
        # the generated OCEL. Should be 1
        # This tests the replay as well as the process execution extraction
        occn = occn_sync()

        parameters = {
            playout_extensive.Parameters.MAX_BINDINGS_PER_ACTIVITY: 3,
            playout_extensive.Parameters.RETURN_SEQUENCES: False,
            playout_extensive.Parameters.OBJECTS_UNIQUE_PER_SEQUENCE: True,
        }

        objects = {"order": {"o1"}, "item": {"i1", "i2"}}
        # Here, the number of sequences and pxs should be the same (540)
        ocel = playout_extensive.apply(occn, objects, parameters)
        fitness = occn_replay_fitness.apply(ocel=ocel, occn=occn)
        self.assertEqual(fitness["no_process_executions"], 540)
        self.assertEqual(fitness["log_fitness"], 1.0)
        
        
        #### Add non-fitting process executions ####
        no_pxs = fitness["no_process_executions"]
        event_id_column = constants.DEFAULT_EVENT_ID
        event_activity = constants.DEFAULT_EVENT_ACTIVITY
        event_timestamp = constants.DEFAULT_EVENT_TIMESTAMP
        object_id_column = constants.DEFAULT_OBJECT_ID
        object_type_column = constants.DEFAULT_OBJECT_TYPE
        
        # Initialize lists and counters
        events_list = []
        objects_list = []
        relations_list = []
        
        # Make sure starting values are higher than existing ones in the OCEL
        event_id_counter = 100000
        trace_counter = 100000
        curr_timestamp = 2000000000
        all_objects_seen = set()
        
        # Helper function to add a single event and its relations
        def add_event(act, obj_tuples):
            """
            Adds an event, its related objects, and relations to the lists.
            
            :param act: Activity name (string)
            :param obj_tuples: List of (object_name, object_type) tuples
            """
            nonlocal event_id_counter, curr_timestamp, trace_counter
            
            # 1. Create Event
            event_id = f"event_{event_id_counter}"
            event_id_counter += 1
            curr_timestamp += 1
            event_time = pd.to_datetime(curr_timestamp, unit="s")

            events_list.append({
                event_id_column: event_id,
                event_activity: act,
                event_timestamp: event_time,
            })

            # 2. Create Objects and Relations
            for obj_name, obj_type in obj_tuples:
                obj_id = f"{obj_name}_{trace_counter}"

                # Add object if not seen before
                if (obj_id, obj_type) not in all_objects_seen:
                    all_objects_seen.add((obj_id, obj_type))
                    objects_list.append({
                        object_id_column: obj_id,
                        object_type_column: obj_type
                    })
                
                # Add relation
                relations_list.append({
                    event_id_column: event_id,
                    event_activity: act,
                    event_timestamp: event_time,
                    object_id_column: obj_id,
                    object_type_column: obj_type,
                })
        
        # Add incomplete trace
        # a (o1) -> b (i1)
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        trace_counter += 1
        no_pxs += 2
        
        # Add incomplete trace
        # a (o1) -> c (o1, i1)
        add_event("a", [("o1", "order")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add incomplete trace
        # a (o1) -> c (o1)
        add_event("a", [("o1", "order")])
        add_event("c", [("o1", "order")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with wrong object
        # a (o1) -> b (i1) -> c (o1, i2)
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        add_event("c", [("o1", "order"), ("i2", "item")])
        trace_counter += 1
        no_pxs += 2
        
        # Add trace with wrong object
        # a (o1) -> b (i2) -> c (o1, i1)
        add_event("a", [("o1", "order")])
        add_event("b", [("i2", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 2
        
        # Add trace with wrong activity order
        # a (o1) -> c (o1, i1) -> b (i1)
        add_event("a", [("o1", "order")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        add_event("b", [("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with wrong activity order
        # c (o1, i1) -> a (o1) -> b (i1)
        add_event("c", [("o1", "order"), ("i1", "item")])
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with wrong activity
        # a (o1) -> a (i1) -> c (o1, i1)
        add_event("a", [("o1", "order")])
        add_event("a", [("i1", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with wrong activity
        # b (o1) -> b (i1) -> c (o1, i1)
        add_event("b", [("o1", "order")])
        add_event("b", [("i1", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with wrong activity
        # a (o1) -> b (i1) -> a (o1, i1)
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        add_event("a", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with redundant activity
        # a (o1) -> a (o1) -> b (i1) -> c (o1, i1)
        add_event("a", [("o1", "order")])
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with redundant activity
        # a (o1) -> b (i1) -> c (o1, i1) -> b (i1)
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        add_event("b", [("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # Add trace with redundant activity
        # a (o1) -> b (i1) -> c (o1, i1) -> c (o1, i1)
        add_event("a", [("o1", "order")])
        add_event("b", [("i1", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        add_event("c", [("o1", "order"), ("i1", "item")])
        trace_counter += 1
        no_pxs += 1
        
        # --- Append all new data to the OCEL ---
        if events_list:
            # Convert lists to DataFrames
            events_df = pd.DataFrame(events_list)
            objects_df = pd.DataFrame(objects_list)
            relations_df = pd.DataFrame(relations_list)

            # Concatenate with existing OCEL DataFrames
            ocel.events = pd.concat([ocel.events, events_df], ignore_index=True)
            ocel.objects = pd.concat([ocel.objects, objects_df], ignore_index=True)
            ocel.relations = pd.concat([ocel.relations, relations_df], ignore_index=True)
        
        
        fitness = occn_replay_fitness.apply(ocel=ocel, occn=occn)
        self.assertEqual(fitness["no_process_executions"], no_pxs)
        # correct pxs should still be 540
        self.assertAlmostEqual(fitness["log_fitness"] * fitness["no_process_executions"], 540.0)
            


def occn_ABC():
    marker_groups = {
        "START_order": {
            "img": [],
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "a": {
            "img": [
                [("START_order", "order", (1, 1), 0)],
            ],
            "omg": [
                [("b", "order", (1, 1), 0)],
            ],
        },
        "b": {
            "img": [
                [("a", "order", (1, 1), 0)],
            ],
            "omg": [
                [("c", "order", (1, 1), 0)],
            ],
        },
        "c": {
            "img": [
                [("b", "order", (1, 1), 0)],
            ],
            "omg": [
                [("END_order", "order", (1, 1), 0)],
            ],
        },
        "END_order": {
            "img": [
                [("c", "order", (1, 1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def occn_sync():
    marker_groups = {
        "START_order": {
            "img": [],
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "START_item": {
            "img": [],
            "omg": [
                [("b", "item", (1, 1), 0)],
            ],
        },
        "a": {
            "img": [
                [("START_order", "order", (1, 1), 0)],
            ],
            "omg": [
                [("c", "order", (1, 1), 0)],
            ],
        },
        "b": {
            "img": [
                [("START_item", "item", (1, 1), 0)],
            ],
            "omg": [
                [("c", "item", (1, 1), 0)],
            ],
        },
        "c": {
            "img": [
                [("a", "order", (1, 1), 0), ("b", "item", (1, -1), 0)],
            ],
            "omg": [
                [("END_order", "order", (1, 1), 0), ("END_item", "item", (1, -1), 0)],
            ],
        },
        "END_order": {
            "img": [
                [("c", "order", (1, 1), 0)],
            ]
        },
        "END_item": {
            "img": [
                [("c", "item", (1, 1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


if __name__ == "__main__":
    unittest.main()

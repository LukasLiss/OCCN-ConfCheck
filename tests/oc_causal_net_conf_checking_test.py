import unittest
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
        
        # Add incomplete trace
        # a (o1) -> b (i1)
            
            


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

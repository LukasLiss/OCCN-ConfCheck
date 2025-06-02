import unittest
import pm4py
from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.oc_causal_net import converter
import networkx as nx

from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net


class OCCausalNetTest(unittest.TestCase):
    def test_constructor_01(self):
        # create OCCN
        arcs = dict()
        arcs["START_order"] = {"a": {"order": {"object_type": "order"}}}
        arcs["START_item"] = {"a": {"item": {"object_type": "item"}}}
        arcs["a"] = {
            "END_order": {"order": {"object_type": "order"}},
            "END_item": {"item": {"object_type": "item"}},
        }

        START_order_output_markers = OCCausalNet.MarkerGroup(
            markers=[OCCausalNet.Marker("a", "order", (1, 1), 0)]
        )

        START_item_output_markers = OCCausalNet.MarkerGroup(
            markers=[OCCausalNet.Marker("a", "item", (1, float("inf")), 0)]
        )

        a_input_markers = OCCausalNet.MarkerGroup(
            markers=[
                OCCausalNet.Marker("START_order", "order", (1, 1), 0),
                OCCausalNet.Marker("START_item", "item", (1, float("inf")), 1),
            ]
        )

        a_output_markers = OCCausalNet.MarkerGroup(
            markers=[
                OCCausalNet.Marker("END_order", "order", (1, 1), 0),
                OCCausalNet.Marker("END_item", "item", (1, float("inf")), 1),
            ]
        )

        END_order_input_markers = OCCausalNet.MarkerGroup(
            markers=[OCCausalNet.Marker("a", "order", (1, 1), 0)]
        )

        END_item_input_markers = OCCausalNet.MarkerGroup(
            markers=[OCCausalNet.Marker("a", "item", (1, float("inf")), 0)]
        )

        occn = OCCausalNet(
            nx.MultiDiGraph(arcs),
            {
                "a": [a_output_markers],
                "START_order": [START_order_output_markers],
                "START_item": [START_item_output_markers],
            },
            {
                "a": [a_input_markers],
                "END_order": [END_order_input_markers],
                "END_item": [END_item_input_markers],
            },
        )

        print("\nTEST OCCN CONSTRUCTOR 01")
        print(occn)

    def test_constructor_02(self):
        # same net as above, but using the create_oc_causal_net function
        marker_groups = {
            "START_order": {
                "omg": [
                    [("a", "order", (1, 1), 0)],
                ],
            },
            "START_item": {
                "omg": [
                    [("a", "item", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [
                        ("START_order", "order", (1, 1), 0),
                        ("START_item", "item", (1, -1), 0),
                    ],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                        ("END_item", "item", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
            },
            "END_item": {
                "img": [
                    [("a", "item", (1, -1), 0)],
                ],
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONSTRUCTOR 02")
        print(occn)

    def test_conversion_basic(self):
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
                    [("END_order", "order", (1, 1), 0)],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\n================TEST OCCN CONVERSION BASIC================")
        print("OCCN:")
        print(occn)
        ocpn = converter.apply(occn)
        print(ocpn)

    def test_conversion_multi(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [("END_order", "order", (1, -1), 0)],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, -1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION MULTI")
        print(occn)

    def test_conversion_combined(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, 1), 0)],
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, 1), 0)],
                ],
                "omg": [
                    [("END_order", "order", (1, 1), 0)],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                    [("a", "order", (1, -1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION COMBINED")
        print(occn)

    def test_conversion_multi_marker(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (2, 2), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                        ("b", "order", (1, 1), 0),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                    [("b", "order", (1, 1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION MULTI MARKER")
        print(occn)

    def test_conversion_multi_square_marker(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, -1), 0), ("b", "order", (1, 1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION SQUARE MARKER")
        print(occn)

    def test_conversion_triple_marker(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 0),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "c": {
                "img": [
                    [("a", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [
                        ("a", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 0),
                    ],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION TRIPLE MARKER")
        print(occn)

    def test_conversion_key(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 1),
                        ("b", "order", (1, 1), 1),
                        ("c", "order", (1, -1), 1),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "c": {
                "img": [
                    [("a", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [
                        ("a", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 0),
                    ],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION KEY")
        print(occn)

    def test_conversion_key_order(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 1),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 1),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "c": {
                "img": [
                    [("a", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [
                        ("a", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 0),
                    ],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION KEY ORDER")
        print(occn)

    def test_conversion_key_order_square(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 1),
                        ("b", "order", (1, -1), 0),
                        ("c", "order", (1, -1), 1),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "c": {
                "img": [
                    [("a", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [
                        ("a", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 0),
                    ],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION KEY ORDER SQUARE")
        print(occn)

    def test_conversion_multi_key(self):
        marker_groups = {
            "START_order": {
                "img": [],
                "omg": [
                    [("a", "order", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [("START_order", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 1),
                        ("b", "order", (1, 1), 1),
                        ("c", "order", (1, -1), 1),
                    ],
                    [
                        ("END_order", "order", (1, -1), 2),
                        ("b", "order", (1, 1), 2),
                    ],
                ],
            },
            "b": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                    ],
                ],
            },
            "c": {
                "img": [
                    [("a", "order", (1, -1), 0)],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [
                        ("a", "order", (1, -1), 0),
                        ("b", "order", (1, 1), 0),
                        ("c", "order", (1, -1), 0),
                    ],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION MULTI KEY")
        print(occn)

    def test_conversion_multi_ot(self):
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
                    [("a", "item", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [
                        ("START_order", "order", (1, 1), 0),
                        ("START_item", "item", (1, -1), 0),
                    ],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                        ("END_item", "item", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ]
            },
            "END_item": {
                "img": [
                    [("a", "item", (1, -1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION MULTI OT")
        print(occn)

    def test_conversion_multi_ot_multi_marker(self):
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
                    [("a", "item", (1, -1), 0)],
                ],
            },
            "a": {
                "img": [
                    [
                        ("START_order", "order", (1, 1), 0),
                        ("START_item", "item", (1, -1), 0),
                    ],
                    [
                        ("START_item", "item", (1, -1), 0),
                    ],
                ],
                "omg": [
                    [
                        ("END_order", "order", (1, 1), 0),
                        ("END_item", "item", (1, -1), 0),
                    ],
                    [
                        ("END_item", "item", (1, -1), 0),
                    ],
                ],
            },
            "END_order": {
                "img": [
                    [("a", "order", (1, 1), 0)],
                ]
            },
            "END_item": {
                "img": [
                    [("a", "item", (1, -1), 0)],
                ]
            },
        }

        occn = create_oc_causal_net(marker_groups)
        print("\nTEST OCCN CONVERSION MULTI OT MULTI MARKER")
        print(occn)

    def test_conversion_ABC(self):
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
        print("\nTEST OCCN CONVERSION ABC")
        print(occn)

    def test_conversion_isolated(self):
        arcs = dict()
        arcs["a"] = {}
        arcs["START_order"] = {}
        arcs["END_order"] = {}

        occn = OCCausalNet(
            nx.MultiDiGraph(arcs),
            {},
            {},
        )

        print("\nTEST OCCN CONVERSION ISOLATED")
        print(occn)


if __name__ == "__main__":
    unittest.main()

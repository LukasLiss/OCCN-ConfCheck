import unittest
import pm4py
from pm4py.objects.oc_causal_net.obj import OCCausalNet
import networkx as nx


def create_oc_causal_net(marker_groups):
    """
    Create an object-centric causal net from a list of marker groups.
    Does not consider activity counts or the relative occurence threshold.
    May mutate the input data.

    Parameters
    ----------
    marker_groups : dict[str, ]
        Dict of marker groups per activity. Syntax:
        {
            "activity_name": {
                "img": [
                    [
                        (activity, object_type, (min_count, max_count), marker_key),
                        // -1 for max_count = inf; 0 for unique marker key
                        ...
                    ],
                    ...
                ],
                "omg": [
                    ...
                ]
            }
            ]
        }

    Returns
    -------
    OCCausalNet
        Object-centric causal net
    """
    # infer activities
    activities = set(marker_groups.keys())

    # get input and output marker groups
    input_marker_groups = {}
    output_marker_groups = {}

    # make all keys=0 unique
    # find max key
    max_key = max(
        [
            key
            for groups in marker_groups.values()
            for group in groups.get("img", []) + groups.get("omg", [])
            for _, _, _, key in group
        ],
        default=0,
    )
    key_counter = max_key + 1

    # give markers with key=0 a unique key and set inf as max count if max count is -1
    for groups in marker_groups.values():
        for group in groups.get("img", []) + groups.get("omg", []):
            for i, (
                related_activity,
                object_type,
                count_range,
                marker_key,
            ) in enumerate(group):
                if marker_key == 0:
                    group[i] = (
                        related_activity,
                        object_type,
                        (
                            count_range
                            if count_range[1] != -1
                            else (count_range[0], float("inf"))
                        ),
                        key_counter,
                    )
                    key_counter += 1
            key_counter = max_key + 1

    for activity, groups in marker_groups.items():
        img = groups.get("img", [])
        omg = groups.get("omg", [])

        if img:
            input_marker_groups[activity] = [
                OCCausalNet.MarkerGroup(
                    markers=[
                        OCCausalNet.Marker(
                            related_activity, object_type, count_range, marker_key
                        )
                        for related_activity, object_type, count_range, marker_key in group
                    ]
                )
                for group in img
            ]
        if omg:
            output_marker_groups[activity] = [
                OCCausalNet.MarkerGroup(
                    markers=[
                        OCCausalNet.Marker(
                            related_activity, object_type, count_range, marker_key
                        )
                        for related_activity, object_type, count_range, marker_key in group
                    ]
                )
                for group in omg
            ]

    # infer arcs from the marker groups
    arcs = dict()
    for activity in activities:
        for group in output_marker_groups.get(activity, []):
            for marker in group.markers:
                related_activity = marker.related_activity
                object_type = marker.object_type
                if activity not in arcs:
                    arcs[activity] = {}
                if related_activity not in arcs[activity]:
                    arcs[activity][related_activity] = {}
                if object_type not in arcs[activity][related_activity]:
                    arcs[activity][related_activity][object_type] = {}
                arcs[activity][related_activity][object_type] = {
                    "object_type": object_type
                }
    # create the dependency graph
    dependency_graph = nx.MultiDiGraph(arcs)

    # create the object-centric causal net
    occn = OCCausalNet(
        dependency_graph,
        output_marker_groups,
        input_marker_groups,
    )
    return occn


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

        print("\n")
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
        print("\n")
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
        print("\n")
        print(occn)

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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
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
        print("\n")
        print(occn)


if __name__ == "__main__":
    unittest.main()

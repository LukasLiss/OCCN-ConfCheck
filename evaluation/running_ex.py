from collections import Counter
from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net
from pm4py.objects.ocpn.obj import OCMarking, OCPetriNet


def ocpn_running_ex():
    places = dict()
    transitions = dict()
    arcs = []

    name = "running_ex_ocpn"
    places["container_source"] = OCPetriNet.Place("container_source", "Container")
    places["c2"] = OCPetriNet.Place("c2", "Container")
    places["c3"] = OCPetriNet.Place("c3", "Container")
    places["container_sink"] = OCPetriNet.Place("container_sink", "Container")

    places["order_source"] = OCPetriNet.Place("order_source", "Order")
    places["o2"] = OCPetriNet.Place("o2", "Order")
    places["o3"] = OCPetriNet.Place("o3", "Order")
    places["o4"] = OCPetriNet.Place("o4", "Order")
    places["o5"] = OCPetriNet.Place("o5", "Order")
    places["o6"] = OCPetriNet.Place("o6", "Order")
    places["order_sink"] = OCPetriNet.Place("order_sink", "Order")

    places["box_source"] = OCPetriNet.Place("box_source", "Box")
    places["b2"] = OCPetriNet.Place("b2", "Box")
    places["box_sink"] = OCPetriNet.Place("box_sink", "Box")

    transitions["c"] = OCPetriNet.Transition("c", "c")
    transitions["f"] = OCPetriNet.Transition("f", "f")
    transitions["e"] = OCPetriNet.Transition("e", "e")
    transitions["a"] = OCPetriNet.Transition("a", "a")
    transitions["silent1"] = OCPetriNet.Transition("silent1", None)
    transitions["b"] = OCPetriNet.Transition("b", "b")
    transitions["s"] = OCPetriNet.Transition("s", "s")
    transitions["d"] = OCPetriNet.Transition("d", "d")
    transitions["r"] = OCPetriNet.Transition("r", "r")
    transitions["ti"] = OCPetriNet.Transition("ti", "ti")
    transitions["si"] = OCPetriNet.Transition("si", "si")
    transitions["silent2"] = OCPetriNet.Transition("silent2", None)
    transitions["da"] = OCPetriNet.Transition("da", "da")
    transitions["ba"] = OCPetriNet.Transition("ba", "ba")
    transitions["silent3"] = OCPetriNet.Transition("silent3", None)

    connect(
        places["container_source"],
        transitions["c"],
        "Container",
        arcs,
        is_variable=False,
    )
    connect(
        places["container_source"],
        transitions["f"],
        "Container",
        arcs,
        is_variable=False,
    )
    connect(transitions["c"], places["c2"], "Container", arcs, is_variable=False)
    connect(transitions["f"], places["c2"], "Container", arcs, is_variable=False)
    connect(places["c2"], transitions["e"], "Container", arcs, is_variable=True)
    connect(transitions["e"], places["c3"], "Container", arcs, is_variable=True)
    connect(places["c3"], transitions["s"], "Container", arcs, is_variable=True)
    connect(
        transitions["s"], places["container_sink"], "Container", arcs, is_variable=True
    )

    connect(places["order_source"], transitions["a"], "Order", arcs, is_variable=False)
    connect(
        places["order_source"], transitions["silent1"], "Order", arcs, is_variable=False
    )
    connect(transitions["a"], places["o2"], "Order", arcs, is_variable=False)
    connect(transitions["silent1"], places["o2"], "Order", arcs, is_variable=False)
    connect(places["o2"], transitions["b"], "Order", arcs, is_variable=False)
    connect(transitions["b"], places["o3"], "Order", arcs, is_variable=False)
    connect(places["o3"], transitions["s"], "Order", arcs, is_variable=True)
    connect(transitions["s"], places["o4"], "Order", arcs, is_variable=True)
    connect(places["o4"], transitions["r"], "Order", arcs, is_variable=True)
    connect(transitions["r"], places["o5"], "Order", arcs, is_variable=True)
    connect(transitions["r"], places["o6"], "Order", arcs, is_variable=True)
    connect(places["o5"], transitions["silent2"], "Order", arcs, is_variable=True)
    connect(places["o5"], transitions["ti"], "Order", arcs, is_variable=False)
    connect(places["o5"], transitions["si"], "Order", arcs, is_variable=True)
    connect(
        transitions["silent2"], places["order_sink"], "Order", arcs, is_variable=True
    )
    connect(transitions["ti"], places["order_sink"], "Order", arcs, is_variable=False)
    connect(transitions["si"], places["order_sink"], "Order", arcs, is_variable=True)
    connect(places["o6"], transitions["silent3"], "Order", arcs, is_variable=True)
    connect(places["o6"], transitions["da"], "Order", arcs, is_variable=False)
    connect(places["o6"], transitions["ba"], "Order", arcs, is_variable=True)
    connect(
        transitions["silent3"], places["order_sink"], "Order", arcs, is_variable=True
    )
    connect(transitions["da"], places["order_sink"], "Order", arcs, is_variable=False)
    connect(transitions["ba"], places["order_sink"], "Order", arcs, is_variable=True)

    connect(places["box_source"], transitions["d"], "Box", arcs, is_variable=False)
    connect(transitions["d"], places["b2"], "Box", arcs, is_variable=False)
    connect(places["b2"], transitions["s"], "Box", arcs, is_variable=True)
    connect(transitions["s"], places["box_sink"], "Box", arcs, is_variable=True)

    initial_marking = OCMarking(
        {
            places["container_source"]: Counter(["c1_0"]),
            places["order_source"]: Counter(["o1_0"]),
            places["box_source"]: Counter(["b1_0"]),
        }
    )

    final_marking = OCMarking(
        {
            places["container_sink"]: Counter(["c1_0"]),
            places["order_sink"]: Counter(["o1_0"]),
            places["box_sink"]: Counter(["b1_0"]),
        }
    )

    ocpn = OCPetriNet(
        name,
        places=list(places.values()),
        transitions=list(transitions.values()),
        arcs=arcs,
        initial_marking=initial_marking,
        final_marking=final_marking,
    )

    return ocpn


def occn_running_ex():
    marker_groups = {
        "START_Container": {
            "omg": [
                [("c", "Container", (1, 1), 0)],
                [("f", "Container", (1, 1), 0)]
            ],
        },
        "c": {
            "img": [
                [("START_Container", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("e", "Container", (1, 1), 0)],
            ],
        },
        "f": {
            "img": [
                [("START_Container", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("e", "Container", (1, 1), 0)],
            ],
        },
        "e": {
            "img": [
                [("c", "Container", (1, 1), 0), ("f", "Container", (1, -1), 0)],
            ],
            "omg": [
                [("s", "Container", (1, -1), 0)],
            ],
        },
        "START_Order": {
            "omg": [
                [("a", "Order", (1, 1), 0)],
                [("b", "Order", (1, 1), 0)],
            ],
        },
        "a": {
            "img": [
                [("START_Order", "Order", (1, 1), 0)],
            ],
            "omg": [
                [("b", "Order", (1, 1), 0)],
            ],
        },
        "b": {
            "img": [
                [("START_Order", "Order", (1, 1), 0)],
                [("a", "Order", (1, 1), 0)],
            ],
            "omg": [
                [("s", "Order", (1, 1), 0)],
            ],
        },
        "START_Box": {
            "omg": [
                [("d", "Box", (1, 1), 0)],
            ],
        },
        "d": {
            "img": [
                [("START_Box", "Box", (1, 1), 0)],
            ],
            "omg": [
                [("s", "Box", (1, 1), 0)],
            ],
        },
        "s": {
            "img": [
                [("e", "Container", (1, 1), 0), ("b", "Order", (1, -1), 0)],
                [("d", "Box", (1, 1), 0), ("b", "Order", (1, 1), 0)],
            ],
            "omg": [
                [("END_Container", "Container", (1, 1), 0), ("r", "Order", (1, -1), 0)],
                [("END_Box", "Box", (1, 1), 0), ("r", "Order", (1, 1), 0)],
            ],
        },
        "END_Container": {
            "img": [
                [("s", "Container", (1, 1), 0)],
            ],
        },
        "END_Box": {
            "img": [
                [("s", "Box", (1, 1), 0)],
            ],
        },
        "r": {
            "img": [
                [("s", "Order", (1, 1), 0)],
                [("s", "Order", (1, -1), 0)],
            ],
            "omg": [
                [
                    ("ti", "Order", (1, 1), 1),
                    ("si", "Order", (0, -1), 1),
                    ("da", "Order", (1, 1), 2),
                    ("ba", "Order", (0, -1), 2),
                ],
            ],
        },
        "ti": {
            "img": [
                [("r", "Order", (1, 1), 0)],
            ],
            "omg": [
                [("END_Order", "Order", (1, 1), 0)],
            ],
        },
        "si": {
            "img": [
                [("r", "Order", (1, -1), 0)],
            ],
            "omg": [
                [("END_Order", "Order", (1, -1), 0)],
            ],
        },
        "da": {
            "img": [
                [("r", "Order", (1, 1), 0)],
            ],
            "omg": [
                [("END_Order", "Order", (1, 1), 0)],
            ],
        },
        "ba": {
            "img": [
                [("r", "Order", (1, -1), 0)],
            ],
            "omg": [
                [("END_Order", "Order", (1, -1), 0)],
            ],
        },
        "END_Order": {
            "img": [
                [("ti", "Order", (1, 1), 0)],
                [("si", "Order", (1, 1), 0)],
                [("da", "Order", (1, 1), 0)],
                [("ba", "Order", (1, 1), 0)],
            ],
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def connect(source, target, object_type, arcs, *, is_variable=False):
    """
    Create an OCPetriNet.Arc, attach it to source/target, store it in `arcs`, and return it.
    """
    arc = OCPetriNet.Arc(source, target, object_type, is_variable=is_variable)
    source.add_out_arc(arc)
    target.add_in_arc(arc)
    arcs.append(arc)
    return arc
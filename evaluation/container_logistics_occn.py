from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net


def occn_container_logistics():
    marker_groups = {
        "START_Container": {
            "omg": [
                [("Order Empty Containers", "Container", (1, 1), 0)],
            ],
        },
        # 1 transport document for >= 1 container(s)
        "Order Empty Containers": {
            "img": [
                [
                    ("START_Container", "Container", (1, -1), 0),
                    ("Book Vehicles", "Transport Document", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Depart", "Transport Document", (1, 1), 0),
                    ("Pick Up Empty Container", "Container", (1, -1), 0),
                ],
            ],
        },
        "Pick Up Empty Container": {
            "img": [
                [("Order Empty Containers", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("Load Truck", "Container", (1, 1), 0)],
            ],
        },
        "START_Handling Unit": {
            "omg": [
                [("Collect Goods", "Handling Unit", (1, 1), 0)],
            ],
        },
        "Collect Goods": {
            "img": [
                [("START_Handling Unit", "Handling Unit", (1, 1), 0)],
            ],
            "omg": [
                [("Load Truck", "Handling Unit", (1, 1), 0)],
            ],
        },
        # = 1 Handling Unit per Container
        "Load Truck": {
            "img": [
                [
                    ("Collect Goods", "Handling Unit", (1, 1), 0),
                    ("Pick Up Empty Container", "Container", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_Handling Unit", "Handling Unit", (1, 1), 0),
                    ("Drive to Terminal", "Container", (1, 1), 0),
                ],
            ],
        },
        "END_Handling Unit": {
            "img": [
                [("Load Truck", "Handling Unit", (1, 1), 0)],
            ],
        },
        "Drive to Terminal": {
            "img": [
                [("Load Truck", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("Weigh", "Container", (1, 1), 0)],
            ],
        },
        "Weigh": {
            "img": [
                [("Drive to Terminal", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("Place in Stock", "Container", (1, 1), 0)],
            ],
        },
        "Place in Stock": {
            "img": [
                [("Weigh", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("Bring to Loading Bay", "Container", (1, 1), 0)],
            ],
        },
        "Bring to Loading Bay": {
            "img": [
                [("Place in Stock", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("Load to Vehicle", "Container", (1, 1), 0)],
            ],
        },
        "Load to Vehicle": {
            "img": [
                [("Bring to Loading Bay", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("Depart", "Container", (1, 1), 0)],
            ],
        },
        "START_Transport Document": {
            "omg": [
                [("Create Transport Document", "Transport Document", (1, 1), 0)],
            ],
        },
        "START_Customer Order": {
            "omg": [
                [("Register Customer Order", "Customer Order", (1, 1), 0)],
            ],
        },
        "Register Customer Order": {
            "img": [
                [("START_Customer Order", "Customer Order", (1, 1), 0)],
            ],
            "omg": [
                [("Create Transport Document", "Customer Order", (1, 1), 0)],
            ],
        },
        "Create Transport Document": {
            "img": [
                [
                    ("START_Transport Document", "Transport Document", (1, 1), 0),
                    ("Register Customer Order", "Customer Order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Book Vehicles", "Transport Document", (1, 1), 0),
                    ("END_Customer Order", "Customer Order", (1, 1), 0),
                ],
            ],
        },
        "END_Customer Order": {
            "img": [
                [("Create Transport Document", "Customer Order", (1, 1), 0)],
            ],
        },
        "Book Vehicles": {
            "img": [
                [("Create Transport Document", "Transport Document", (1, 1), 0)],
            ],
            "omg": [
                [("Order Empty Containers", "Transport Document", (1, 1), 0)],
            ],
        },
        "Depart": {
            "img": [
                [
                    ("Order Empty Containers", "Transport Document", (1, 1), 0),
                    ("Load to Vehicle", "Container", (1, -1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_Transport Document", "Transport Document", (1, 1), 0),
                    ("END_Container", "Container", (1, -1), 0),
                ],
            ],
        },
        "END_Transport Document": {
            "img": [
                [("Depart", "Transport Document", (1, 1), 0)],
            ],
        },
        "END_Container": {
            "img": [
                [("Depart", "Container", (1, 1), 0)],
            ],
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn
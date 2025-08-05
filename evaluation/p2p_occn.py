

from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net


def occn_p2p():
    marker_groups = {
        "START_material": {
            "omg": [
                [("Create Purchase Requisition", "material", (1, -1), 0)],
            ],
        },
        "START_purchase_requisition": {
            "omg": [
                [("Create Purchase Requisition", "purchase_requisition", (1, -1), 0)],
            ],
        },
        # >= 1 material per purchase requisition
        "Create Purchase Requisition": {
            "img": [
                [
                    ("START_material", "material", (1, -1), 0),
                    ("START_purchase_requisition", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Approve Purchase Requisition", "material", (1, -1), 0),
                    ("Approve Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
                [
                    ("Delegate Purchase Requisition Approval", "material", (1, -1), 0),
                    ("Delegate Purchase Requisition Approval", "purchase_requisition", (1, 1), 0),
                ],
            ],
        },
        "Approve Purchase Requisition": {
            "img": [
                [
                    ("Create Purchase Requisition", "material", (1, -1), 0),
                    ("Create Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_material", "material", (1, -1), 0),
                    ("Create Request for Quotation", "purchase_requisition", (1, 1), 0),
                ],
            ],
        },
        "Delegate Purchase Requisition Approval": {
            "img": [
                [
                    ("Create Purchase Requisition", "material", (1, -1), 0),
                    ("Create Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_material", "material", (1, -1), 0),
                    ("Create Request for Quotation", "purchase_requisition", (1, 1), 0),
                ],
            ],
        },
        "END_material": {
            "img": [
                [("Approve Purchase Requisition", "material", (1, -1), 0)],
                [("Delegate Purchase Requisition Approval", "material", (1, -1), 0)],
            ],
        },
        "START_quotation": {
            "omg": [
                [("Create Request for Quotation", "quotation", (1, -1), 0)],
            ],
        },
        "Create Request for Quotation": {
            "img": [
                [
                    ("START_quotation", "quotation", (1, 1), 0),
                    ("Approve Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
                [
                    ("START_quotation", "quotation", (1, 1), 0),
                    ("Delegate Purchase Requisition Approval", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_purchase_requisition", "purchase_requisition", (1, 1), 0),
                    ("Create Purchase Order", "quotation", (1, 1), 0),
                ],
            ],
        },
        "END_purchase_requisition": {
            "img": [
                [("Create Request for Quotation", "purchase_requisition", (1, -1), 0)],
            ],
        },
        "START_purchase_order": {
            "omg": [
                [("Create Purchase Order", "purchase_order", (1, -1), 0)],
            ],
        },
        "Create Purchase Order": {
            "img": [
                [
                    ("Create Request for Quotation", "quotation", (1, 1), 0),
                    ("START_purchase_order", "purchase_order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Approve Purchase Order", "quotation", (1, 1), 0),
                    ("Approve Purchase Order", "purchase_order", (1, 1), 0),
                ],
            ],
        },
        "Approve Purchase Order": {
            "img": [
                [
                    ("Create Purchase Order", "quotation", (1, 1), 0),
                    ("Create Purchase Order", "purchase_order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_quotation", "quotation", (1, 1), 0),
                    ("Create Goods Receipt", "purchase_order", (1, 1), 0),
                ],
            ],
        },
        "END_quotation": {
            "img": [
                [("Approve Purchase Order", "quotation", (1, -1), 0)],
            ],
        },
        "START_goods receipt": {
            "omg": [
                [("Create Goods Receipt", "goods receipt", (1, -1), 0)],
            ],
        },
        # 1 purchase_order => n goods receipt / invoice receipt
        # 1 purchase order => 1 payment
        "Create Goods Receipt": {
            "img": [
                [
                    ("START_goods receipt", "goods receipt", (1, -1), 0),
                    ("Approve Purchase Order", "purchase_order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Create Invoice Receipt", "goods receipt", (1, -1), 0),
                    ("Execute Payment", "purchase_order", (1, 1), 0),
                ],
            ],
        },
        "START_invoice receipt": {
            "omg": [
                [("Create Invoice Receipt", "invoice receipt", (1, -1), 0)],
            ],
        },
        "Create Invoice Receipt": {
            "img": [
                [
                    ("START_invoice receipt", "invoice receipt", (1, 1), 0),
                    ("Create Goods Receipt", "goods receipt", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Perform Two-Way Match", "invoice receipt", (1, 1), 0),
                    ("Perform Two-Way Match", "goods receipt", (1, 1), 0),
                ],
            ],
        },
        "Perform Two-Way Match": {
            "img": [
                [
                    ("Create Invoice Receipt", "invoice receipt", (1, 1), 0),
                    ("Create Invoice Receipt", "goods receipt", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Execute Payment", "invoice receipt", (1, 1), 0),
                    ("Execute Payment", "goods receipt", (1, 1), 0),
                ],
            ],
        },
        "START_payment": {
            "omg": [
                [("Execute Payment", "payment", (1, -1), 0)],
            ],
        },
        "Execute Payment": {
            "img": [
                [
                    ("Perform Two-Way Match", "goods receipt", (1, -1), 0),
                    ("Perform Two-Way Match", "invoice receipt", (1, -1), 0),
                    ("Create Goods Receipt", "purchase_order", (1, 1), 0),
                    ("START_payment", "payment", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_goods receipt", "goods receipt", (1, -1), 0),
                    ("END_invoice receipt", "invoice receipt", (1, -1), 0),
                    ("END_purchase_order", "purchase_order", (1, 1), 0),
                    ("END_payment", "payment", (1, 1), 0),
                ],
            ],
        },
        "END_goods receipt": {
            "img": [
                [("Execute Payment", "goods receipt", (1, -1), 0)],
            ],
        },
        "END_invoice receipt": {
            "img": [
                [("Execute Payment", "invoice receipt", (1, -1), 0)],
            ],
        },
        "END_payment": {
            "img": [
                [("Execute Payment", "payment", (1, -1), 0)],
            ],
        },
        "END_purchase_order": {
            "img": [
                [("Execute Payment", "purchase_order", (1, -1), 0)],
            ],
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def occn_p2p_small(): # fewer ot
    marker_groups = {
        "START_material": {
            "omg": [
                [("Create Purchase Requisition", "material", (1, -1), 0)],
            ],
        },
        "START_purchase_requisition": {
            "omg": [
                [("Create Purchase Requisition", "purchase_requisition", (1, -1), 0)],
            ],
        },
        # >= 1 material per purchase requisition
        "Create Purchase Requisition": {
            "img": [
                [
                    ("START_material", "material", (1, -1), 0),
                    ("START_purchase_requisition", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Approve Purchase Requisition", "material", (1, -1), 0),
                    ("Approve Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
                [
                    ("Delegate Purchase Requisition Approval", "material", (1, -1), 0),
                    ("Delegate Purchase Requisition Approval", "purchase_requisition", (1, 1), 0),
                ],
            ],
        },
        "Approve Purchase Requisition": {
            "img": [
                [
                    ("Create Purchase Requisition", "material", (1, -1), 0),
                    ("Create Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_material", "material", (1, -1), 0),
                    ("Create Request for Quotation", "purchase_requisition", (1, 1), 0),
                ],
            ],
        },
        "Delegate Purchase Requisition Approval": {
            "img": [
                [
                    ("Create Purchase Requisition", "material", (1, -1), 0),
                    ("Create Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_material", "material", (1, -1), 0),
                    ("Create Request for Quotation", "purchase_requisition", (1, 1), 0),
                ],
            ],
        },
        "END_material": {
            "img": [
                [("Approve Purchase Requisition", "material", (1, -1), 0)],
                [("Delegate Purchase Requisition Approval", "material", (1, -1), 0)],
            ],
        },
        "START_quotation": {
            "omg": [
                [("Create Request for Quotation", "quotation", (1, -1), 0)],
            ],
        },
        "Create Request for Quotation": {
            "img": [
                [
                    ("START_quotation", "quotation", (1, 1), 0),
                    ("Approve Purchase Requisition", "purchase_requisition", (1, 1), 0),
                ],
                [
                    ("START_quotation", "quotation", (1, 1), 0),
                    ("Delegate Purchase Requisition Approval", "purchase_requisition", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_purchase_requisition", "purchase_requisition", (1, 1), 0),
                    ("Create Purchase Order", "quotation", (1, 1), 0),
                ],
            ],
        },
        "END_purchase_requisition": {
            "img": [
                [("Create Request for Quotation", "purchase_requisition", (1, -1), 0)],
            ],
        },
        "START_purchase_order": {
            "omg": [
                [("Create Purchase Order", "purchase_order", (1, -1), 0)],
            ],
        },
        "Create Purchase Order": {
            "img": [
                [
                    ("Create Request for Quotation", "quotation", (1, 1), 0),
                    ("START_purchase_order", "purchase_order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Approve Purchase Order", "quotation", (1, 1), 0),
                    ("Approve Purchase Order", "purchase_order", (1, 1), 0),
                ],
            ],
        },
        "Approve Purchase Order": {
            "img": [
                [
                    ("Create Purchase Order", "quotation", (1, 1), 0),
                    ("Create Purchase Order", "purchase_order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_quotation", "quotation", (1, 1), 0),
                    ("Create Goods Receipt", "purchase_order", (1, 1), 0),
                ],
            ],
        },
        "END_quotation": {
            "img": [
                [("Approve Purchase Order", "quotation", (1, -1), 0)],
            ],
        },
        # 1 purchase order => 1 payment
        "Create Goods Receipt": {
            "img": [
                [
                    ("Approve Purchase Order", "purchase_order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("Execute Payment", "purchase_order", (1, 1), 0),
                ],
            ],
        },
        "START_payment": {
            "omg": [
                [("Execute Payment", "payment", (1, -1), 0)],
            ],
        },
        "Execute Payment": {
            "img": [
                [
                    ("Create Goods Receipt", "purchase_order", (1, 1), 0),
                    ("START_payment", "payment", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_purchase_order", "purchase_order", (1, 1), 0),
                    ("END_payment", "payment", (1, 1), 0),
                ],
            ],
        },
        "END_payment": {
            "img": [
                [("Execute Payment", "payment", (1, -1), 0)],
            ],
        },
        "END_purchase_order": {
            "img": [
                [("Execute Payment", "purchase_order", (1, -1), 0)],
            ],
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn
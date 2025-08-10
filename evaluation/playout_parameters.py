from converted_ocpn_semantics import _is_final_leq as is_final_leq


def playout_parameters(ocel_name, config_id, playout_mode):
    """
    Specifies parameters for OCPN play-out based on the OCEL name and configuration ID.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file.
    config_id : int
        The configuration ID.
    playout_mode : str
        The playout algorithm used, either:
            - "ocpn_replay_on_converted_occn"
            - "occn_replay_on_original_ocpn"
            - "occn_replay_on_converted_ocpn"
            - "ocpn_replay_on_original_occn"

    Returns
    -------
    dict
        A dictionary with parameters for the OCPN play-out.
            - "object_numbers": A dictionary mapping object types to their respective counts in the initial marking.
            - "final_object_multiplicities": A dictionary mapping object types to their respective counts per object of that type in the final marking.
            - "parameters": dictionary
                - parameters for the play-out algorithm, depending on playout_mode
    """
    final_object_multiplicities = None
    if ocel_name == "ContainerLogistics.json":
        if config_id == 0:  # smallest example
            original_ocpn_branching_factor = 1.4
            converted_occn_branching_factor = 1.2
            original_occn_branching_factor = 1.1
            converted_ocpn_branching_factor = 1.2
            max_bindings_per_activity = 4
            object_numbers = {
                "Customer Order": 1,
                "Transport Document": 1,
                "Vehicle": 1,
                "Container": 2,
                "Truck": 1,
                "Handling Unit": 2,
                "Forklift": 1,
            }
        elif config_id == 1:  # double in size
            original_ocpn_branching_factor = 1.2
            converted_occn_branching_factor = 1.2
            max_bindings_per_activity = 6
            object_numbers = {
                "Customer Order": 2,
                "Transport Document": 2,
                "Vehicle": 4,
                "Container": 4,
                "Truck": 1,
                "Handling Unit": 4,
                "Forklift": 1,
            }
        elif config_id == 2:  # subset of ots (for occn)
            original_ocpn_branching_factor = 1.4
            converted_occn_branching_factor = 1.2
            original_occn_branching_factor = 1.2
            converted_ocpn_branching_factor = 1.3
            max_bindings_per_activity = 5
            object_numbers = {
                "Customer Order": 2,
                "Transport Document": 2,
                "Container": 2,
                "Handling Unit": 2,
            }
    elif ocel_name == "ocel2-p2p.json":
        if config_id == 0:
            original_ocpn_branching_factor = 1.6
            converted_occn_branching_factor = 1.25
            original_occn_branching_factor = 1.5
            converted_ocpn_branching_factor = 4
            max_bindings_per_activity = 5
            object_numbers = {
                "goods receipt": 1,
                "invoice receipt": 1,
                "material": 1,
                "purchase_order": 1,
                "purchase_requisition": 1,
                "quotation": 1,
                "payment": 1,
            }
        if config_id == 1:
            original_ocpn_branching_factor = 1.6
            converted_occn_branching_factor = 1.25
            original_occn_branching_factor = 1.4
            converted_ocpn_branching_factor = 1.2
            max_bindings_per_activity = 5
            object_numbers = {
                "goods receipt": 2,
                "invoice receipt": 2,
                "material": 2,
                "purchase_order": 1,
                "purchase_requisition": 1,
                "quotation": 1,
                "payment": 1,
            }
    elif ocel_name == "ocel2-p2p-small.json":
        if config_id == 0:
            original_ocpn_branching_factor = 1.6
            converted_occn_branching_factor = 1.25
            original_occn_branching_factor = 1.5
            converted_ocpn_branching_factor = 4
            max_bindings_per_activity = 5
            object_numbers = {
                "material": 1,
                "purchase_order": 1,
                "purchase_requisition": 1,
                "quotation": 1,
                "payment": 1,
            }
    elif ocel_name == "ocel2-p2p-smaller.json":
        if config_id == 0:
            original_ocpn_branching_factor = 1.6
            converted_occn_branching_factor = 1.25
            original_occn_branching_factor = 1.5
            converted_ocpn_branching_factor = 1.5
            max_bindings_per_activity = 5
            object_numbers = {
                "purchase_order": 1,
                "purchase_requisition": 1,
                "quotation": 1,
                "payment": 1,
            }
            
    elif ocel_name == "running_ex":
        if config_id == 0:
            original_ocpn_branching_factor = 1.2
            converted_occn_branching_factor = 1.1
            original_occn_branching_factor = 1.3
            converted_ocpn_branching_factor = 1.5
            max_bindings_per_activity = 10
            object_numbers = {
                "Container": 1,
                "Order": 4,
                "Box": 1,
            }

        elif config_id == 1:  # smallest example
            original_ocpn_branching_factor = 1.2
            converted_occn_branching_factor = 1.1
            original_occn_branching_factor = 100
            converted_ocpn_branching_factor = 1.1
            max_bindings_per_activity = 10
            object_numbers = {
                "Container": 0,
                "Order": 1,
                "Box": 1,
            }
        
        elif config_id == 2:  # no boxes, 2 containers
            original_ocpn_branching_factor = 1.2
            converted_occn_branching_factor = 1.1
            original_occn_branching_factor = 1.2
            converted_ocpn_branching_factor = 1.1
            max_bindings_per_activity = 10
            object_numbers = {
                "Container": 2,
                "Order": 3,
                "Box": 0,
            }
        
        elif config_id == 3: 
            original_ocpn_branching_factor = 1.2
            converted_occn_branching_factor = 1.1
            original_occn_branching_factor = 1.25
            converted_ocpn_branching_factor = 1.4
            max_bindings_per_activity = 10
            object_numbers = {
                "Container": 2,
                "Order": 3,
                "Box": 1,
            }

        final_object_multiplicities = {
            "Container": 1,
            "Order": 2,
            "Box": 1,
        }

    if playout_mode == "ocpn_replay_on_converted_occn":
        parameters = {
            "maxBindingsPerActivity": max_bindings_per_activity,
            "branchingFactorTransitions": original_ocpn_branching_factor,
            "branchingFactorBindings": original_ocpn_branching_factor,
            "return_traces": True,
        }
    elif playout_mode == "occn_replay_on_original_ocpn":
        parameters = {
            "maxBindingsPerActivity": max_bindings_per_activity,
            "branching_factor_activities": converted_occn_branching_factor,
            "branching_factor_bindings": converted_occn_branching_factor,
            "return_sequences": True,
        }
    elif playout_mode == "occn_replay_on_converted_ocpn":
        parameters = {
            "maxBindingsPerActivity": max_bindings_per_activity,
            "branching_factor_activities": original_occn_branching_factor,
            "branching_factor_bindings": original_occn_branching_factor,
            "return_sequences": True,
        }
    elif playout_mode == "ocpn_replay_on_original_occn":
        parameters = {
            "maxBindingsPerActivity": max_bindings_per_activity,
            "branchingFactorTransitions": converted_ocpn_branching_factor,
            "branchingFactorBindings": converted_ocpn_branching_factor,
            "return_traces": True,
            "is_final_func": is_final_leq,
        }
    else:
        raise ValueError(f"Invalid playout_mode: {playout_mode}.")

    if not final_object_multiplicities:
        final_object_multiplicities = {ot: 1 for ot in object_numbers.keys()}

    return {
        "parameters": parameters,
        "object_numbers": object_numbers,
        "final_object_multiplicities": final_object_multiplicities,
    }
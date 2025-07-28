from collections import Counter, defaultdict
import re
import time
import pm4py
import os
import statistics
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.align import Align
from rich import box

from pm4py.objects.oc_causal_net.converted_occn_semantics import (
    ConvertedOCCausalNetSemantics,
)
from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net
from pm4py.objects.oc_causal_net.semantics import OCCausalNetSemantics
from pm4py.objects.ocpn import factory as ocpn_factory
from pm4py.objects.ocpn import converter as ocpn_converter
from pm4py.objects.oc_causal_net import converter as occn_converter
from pm4py.algo.simulation.playout.ocpn.variants.extensive import (
    apply as playout_ocpn_extensive,
)
from pm4py.algo.simulation.playout.oc_causal_net.variants.extensive import (
    apply as playout_occn_extensive,
)
from pm4py.objects.ocpn.converted_ocpn_semantics import ConvertedOCPetriNetSemantics
from pm4py.objects.ocpn.converted_ocpn_semantics import _is_final_leq as is_final_leq
from pm4py.objects.ocpn.obj import OCMarking, OCPetriNet
from pm4py.objects.ocpn.semantics import OCPetriNetSemantics


def evaluation():

    # ocels = ["ContainerLogistics.json"]
    ocels = ["running_ex_ocpn"]
    config_id = 1
    time_budget = 14 * 60 * 60  # seconds

    # Discover OCPN -> convert to OCCN -> play-out and replay for both directions
    #eval_ocpn(ocels, time_budget)

    # Discover OCCN -> convert to OCPN -> play-out and replay for both directions
    eval_occn(ocels, time_budget, config_id=config_id)


def eval_ocpn(ocels, time_budget):
    """
    Discover OCPN, convert to OCCN, and perform play-out and replay for both directions.

    Parameters
    ----------
    ocels : list of str
        List of OCEL names to evaluate.
    time_budget : int
        Time budget for each evaluation in seconds.
    """
    for ocel_name in ocels:

        # Discover OCPN
        if ocel_name == "running_ex_ocpn":
            ocpn = ocpn_running_ex()
        else:
            ocpn = discover_ocpn(ocel_name)

        # Convert to OCCausalNet object
        occn = ocpn_converter.apply(
            ocpn, variant=ocpn_converter.Variants.TO_OC_CAUSAL_NET
        )

        # Playout OCPN and replay on OCCN
        playout_ocpn_replay_on_converted_occn(ocpn, occn, ocel_name, time_budget)

        # Playout OCCN and replay on original OCPN
        #playout_converted_occn_replay_on_ocpn(ocpn, occn, ocel_name, time_budget)


def eval_occn(ocels, time_budget, config_id):
    """
    Discover OCCN, convert to OCPN, and perform play-out and replay for both directions.

    Parameters
    ----------
    ocels : list of str
        List of OCEL names to evaluate.
    time_budget : int
        Time budget for each evaluation in seconds.
    config_id : int
        Configuration ID to use for the play-out parameters.
    """
    for ocel_name in ocels:

        if ocel_name == "running_ex_ocpn":
            occn = occn_running_ex()
        else:
            occn = discover_occn(ocel_name)

        # Convert to OCPetriNet object
        ocpn = occn_converter.apply(occn, variant=occn_converter.Variants.TO_OCPN)

        # Playout OCCN and replay on OCPN
        playout_occn_replay_on_converted_ocpn(occn, ocpn, ocel_name, time_budget, config_id=config_id)

        # Playout OCPN and replay on original OCCN
        #playout_ocpn_replay_on_original_occn(ocpn, occn, ocel_name, time_budget)


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
    elif ocel_name == "running_ex_ocpn":
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
            max_bindings_per_activity = 100
            object_numbers = {
                "Container": 0,
                "Order": 1,
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
            "is_final_func": is_final_leq
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


def discover_ocpn(ocel_name):
    """
    This function reads the OCEL, discovers the OCPetriNet, and saves a visualization.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file (e.g., "ContainerLogistics.json").
        The OCEL file should be located in the "evaluation/event_logs" directory.
        The visualization will be saved in the "evaluation/discovered_ocpns" directory.

    Returns
    -------
    OCPetriNet
        The discovered OCPetriNet object.
    """
    # Get path
    ocel_path = os.path.join("evaluation", "event_logs", ocel_name)
    ocel = pm4py.read_ocel2(ocel_path)
    ocpn = pm4py.discover_oc_petri_net(ocel)
    # create discovered_ocpns directory if it doesn't exist
    if not os.path.exists("evaluation/discovered_ocpns"):
        os.makedirs("evaluation/discovered_ocpns")
    # Save visualization
    path_png = os.path.join(
        "evaluation", "discovered_ocpns", f"{os.path.basename(ocel_path)}.png"
    )
    pm4py.save_vis_ocpn(ocpn, path_png)
    # convert to OCPetriNet object
    ocpn_obj = ocpn_factory.create(ocpn)

    return ocpn_obj


def discover_occn(ocel_name):
    """
    This function reads the OCEL, discovers the OCCausalNet, and saves a visualization.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file (e.g., "ContainerLogistics.json").
        The OCEL file should be located in the "evaluation/event_logs" directory.
        The visualization will be saved in the "evaluation/discovered_occn" directory.

    Returns
    -------
    OCCausalNet
        The discovered OCCausalNet object.
    """
    raise NotImplementedError()


def playout_config(ocel_name, ocpn, playout_mode, config_id=0):
    """
    This function returns the configuration for the play-out based on the OCEL name and config ID.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file.
    ocpn : OCPetriNet
        The OCPetriNet object.
    playout_mode : str
        Play-out mode. See `playout_parameters` for valid modes.
    config_id : int, optional
        The configuration ID (default is 0).

    Returns
    -------
    dict
        The configuration dictionary for the OCPN/OCCN play-out.
            - "initial_marking": The initial marking of the OCPN.
            - "final_marking": The final marking of the OCPN.
            - "objects": A dictionary mapping object types to sets of object IDs that occur in the markings.
            - "parameters": The parameters for the play-out algorithm.
    """
    ocel_params = playout_parameters(ocel_name, config_id, playout_mode=playout_mode)

    # get source & target places of the ocpn
    source_places = {}
    sink_places = {}
    pattern_occn_to_ocpn_start_places = r"^p_START_(.+)_i_\1$"
    pattern_occn_to_ocpn_end_places = r"^p_END_(.+)_o_\1$"
    for place in ocpn.places:
        if place.name.endswith("source") or re.fullmatch(
            pattern_occn_to_ocpn_start_places, place.name
        ):
            source_places[place.object_type] = place
        elif place.name.endswith("sink") or re.fullmatch(
            pattern_occn_to_ocpn_end_places, place.name
        ):
            sink_places[place.object_type] = place

    # get initial and final markings
    initial_marking = {
        source_places[obj_type]: Counter([f"{obj_type}_{i}" for i in range(obj_count)])
        for obj_type, obj_count in ocel_params["object_numbers"].items()
    }

    final_marking = {
        sink_places[obj_type]: Counter(
            {
                f"{obj_type}_{i}": ocel_params["final_object_multiplicities"][obj_type]
                for i in range(obj_count)
            }
        )
        for obj_type, obj_count in ocel_params["object_numbers"].items()
    }

    objects = {
        obj_type: {f"{obj_type}_{i}" for i in range(obj_count)}
        for obj_type, obj_count in ocel_params["object_numbers"].items()
    }

    return {
        "initial_marking": OCMarking(initial_marking),
        "final_marking": OCMarking(final_marking),
        "objects": objects,
        "parameters": ocel_params["parameters"],
    }


def playout_ocpn_replay_on_converted_occn(
    ocpn, occn, ocel_name, time_budget, config_id=0
):
    """
    Generate random traces from the OCPN and replay them on the converted OCCN.

    Parameters
    ----------
    ocpn : OCPetriNet
        The OCPetriNet object to play out.
    occn : OCCausalNet
        The OCCausalNet object to replay the traces on.
    ocel_name : str
        The name of the OCEL file, used for getting parameters and logging.
    time_budget : int
        The time budget for the play-out process in seconds.
    """
    _execute_ocpn_playout_and_replay_on_occn(
        ocpn,
        occn,
        ocel_name,
        time_budget,
        config_id,
        playout_mode="ocpn_replay_on_converted_occn",
        header_title="OCPN Playout & Replay on converted OCCN",
    )


def playout_ocpn_replay_on_original_occn(
    ocpn, occn, ocel_name, time_budget, config_id=0
):
    """
    Generate random traces from the OCPN and replay them on the original OCCN.

    Parameters
    ----------
    ocpn : OCPetriNet
        The OCPetriNet object to play out.
    occn : OCCausalNet
        The OCCausalNet object to replay the traces on.
    ocel_name : str
        The name of the OCEL file, used for getting parameters and logging.
    time_budget : int
        The time budget for the play-out process in seconds.
    """
    precomputed = ConvertedOCPetriNetSemantics.precompute_ocpn_replay_params(ocpn, occn)

    _execute_ocpn_playout_and_replay_on_occn(
        ocpn,
        occn,
        ocel_name,
        time_budget,
        config_id,
        playout_mode="ocpn_replay_on_original_occn",
        header_title="OCPN Playout & Replay on original OCCN",
        precomputed=precomputed,
    )


def _execute_ocpn_playout_and_replay_on_occn(
    ocpn, occn, ocel_name, time_budget, config_id, playout_mode, header_title, precomputed=None
):
    """
    Computes play-out for an OCPetriNet and replays the traces on the OCCausalNet.
    The playout mode determines whether the ocpn was converted to the occn or vice versa.

    Parameters
    ----------
    ocpn : OCPetriNet
        The OCPetriNet object to play out.
    occn : OCCausalNet
        The OCCausalNet object to replay the traces on.
    ocel_name : str
        The name of the OCEL file, used for getting parameters and logging.
    time_budget : int
        The time budget for the play-out process in seconds.
    config_id : int
        The configuration ID to use.
    playout_mode : str
        The playout algorithm used, either:
        - "ocpn_replay_on_original_occn"
        - "ocpn_replay_on_converted_occn"
    header_title : str
        The title for the header in the console output.
    precomputed : dict, optional
        Additional precomputed parameters for the play-out algorithm, by default None.
        Required for "ocpn_replay_on_original_occn".
    """
    # --- Configuration Setup ---
    config = playout_config(
        ocel_name, ocpn, playout_mode=playout_mode, config_id=config_id
    )
    initial_marking = config["initial_marking"]
    final_marking = config["final_marking"]
    
    if playout_mode == "ocpn_replay_on_original_occn":
        assert precomputed is not None, "Precomputed parameters are required for this playout mode."
    
        # Add binding token to both markings
        global_binding_place = precomputed["global_binding_place"]
        initial_marking = ConvertedOCPetriNetSemantics._add_binding_token(initial_marking, global_binding_place)
        final_marking = ConvertedOCPetriNetSemantics._add_binding_token(final_marking, global_binding_place)
    
    parameters = config["parameters"]

    # --- UI and Statistics Initialization ---
    console = Console()
    stats = ReplayStatistics(time_budget)
    print_header(
        console,
        header_title,
        ocel_name,
        time_budget,
        config,
    )

    # --- Main Loop with Live Display ---
    with Live(
        stats.get_live_layout(),
        console=console,
        screen=False,
        refresh_per_second=4,
        vertical_overflow="visible",
    ) as live:
        while stats.passed_time < time_budget:
            iter_start_time = time.time()

            # Perform play-out
            (traces, idx_to_transition, id_to_obj_type) = playout_ocpn_extensive(
                ocpn, initial_marking, final_marking, parameters=parameters
            )

            # Perform replay
            failed_replays = _perform_replay_on_occn(
                playout_mode, occn, traces, idx_to_transition, id_to_obj_type, precomputed=precomputed
            )

            # Update statistics and refresh the live display
            iter_time = time.time() - iter_start_time
            stats.update(len(traces), failed_replays, iter_time)
            live.update(stats.get_live_layout())

    # --- Footer ---
    print_footer(console)


def _perform_replay_on_occn(
    playout_mode, occn, traces, idx_to_transition, id_to_obj_type, precomputed=None
):
    """
    Performs replay on the OCCausalNet based on the specified playout mode.

    Parameters
    ----------
    playout_mode : str
        The playout mode used, either:
            - "ocpn_replay_on_original_occn"
            - "ocpn_replay_on_converted_occn"
    occn : OCCausalNet
        The OCCausalNet object to replay the traces on.
    traces : list of list of tuples
        The traces to replay.
    idx_to_transition : dict
        Mapping from index to transition for the OCCN.
    id_to_obj_type : dict
        Mapping from ID to object type for the OCCN.
    precomputed : dict, optional
        Additional precomputed parameters for the replay, by default None. Required for "ocpn_replay_on_original_occn".

    Returns
    -------
    int
        The number of failed replays.
    """
    if playout_mode == "ocpn_replay_on_original_occn":
        return replay_on_original_occn(occn, traces, idx_to_transition, id_to_obj_type, precomputed=precomputed)
    elif playout_mode == "ocpn_replay_on_converted_occn":
        return replay_on_converted_occn(occn, traces, idx_to_transition, id_to_obj_type)
    else:
        raise ValueError(f"Unknown playout mode: {playout_mode}")


def playout_converted_occn_replay_on_ocpn(
    ocpn, occn, ocel_name, time_budget, config_id=0
):
    """
    Generate random traces from the transformed OCCN and replay them on the original OCPN.

    Parameters
    ----------
    ocpn : OCPetriNet
        The original OCPetriNet object to replay the traces on.
    occn : OCCausalNet
        The transformed OCCausalNet object to use for play-out.
    ocel_name : str
        The name of the OCEL file, used for getting parameters and logging.
    time_budget : int
        The time budget for the play-out process in seconds.
    config_id : int, optional
        The configuration ID to use, by default 0.
    """
    _execute_occn_playout_and_replay_on_ocpn(
        ocpn=ocpn,
        occn=occn,
        ocel_name=ocel_name,
        time_budget=time_budget,
        config_id=config_id,
        playout_mode="occn_replay_on_original_ocpn",
        header_title="OCCN Playout & Replay on original OCPN",
    )


def playout_occn_replay_on_converted_ocpn(
    occn, ocpn, ocel_name, time_budget, config_id=0
):
    """
    Generate random traces from the OCCN and replay them on the converted OCPN.

    Parameters
    ----------
    occn : OCCausalNet
        The OCCausalNet object to play out.
    ocpn : OCPetriNet
        The OCPetriNet object to replay the traces on.
    ocel_name : str
        The name of the OCEL file, used for getting parameters and logging.
    time_budget : int
        The time budget for the play-out process in seconds.
    config_id : int, optional
        The configuration ID to use, by default 0.
    """
    # Pre-compute additional parameters for replay
    precomputed = ConvertedOCPetriNetSemantics.precompute_ocpn_replay_params(ocpn, occn)

    _execute_occn_playout_and_replay_on_ocpn(
        ocpn=ocpn,
        occn=occn,
        ocel_name=ocel_name,
        time_budget=time_budget,
        config_id=config_id,
        playout_mode="occn_replay_on_converted_ocpn",
        header_title="OCCN Playout & Replay on converted OCPN",
        precomputed=precomputed,
    )


def _execute_occn_playout_and_replay_on_ocpn(
    ocpn,
    occn,
    ocel_name,
    time_budget,
    config_id,
    playout_mode,
    header_title,
    precomputed=None,
):
    """
    Computes play-out for an OCCausalNet and replays the sequences on the OCPetriNet.
    The playout mode determines whether the ocpn was converted to the occn or vice versa.

    Parameters
    ----------
    ocpn : OCPetriNet
        The OCPetriNet object to replay the traces on.
    occn : OCCausalNet
        The OCCausalNet object to use for play-out.
    ocel_name : str
        The name of the OCEL file, used for getting parameters and logging.
    time_budget : int
        The time budget for the play-out process in seconds.
    config_id : int
        The configuration ID to use, by default 0.
    playout_mode : str
        The playout algorithm used, either:
            - "occn_replay_on_original_ocpn"
            - "occn_replay_on_converted_ocpn"
    header_title : str
        The title for the header in the console output.
    precomputed : dict, optional
        Additional precomputed parameters for the play-out algorithm, by default None.
    """
    # --- Configuration Setup ---
    config = playout_config(
        ocel_name, ocpn, config_id=config_id, playout_mode=playout_mode
    )
    objects = config["objects"]
    parameters = config["parameters"]
    ocpn_initial_marking = config["initial_marking"]
    ocpn_final_marking = config["final_marking"]
    
    # Memo sets used for playout mode "occn_replay_on_converted_ocpn"
    memo_reachable = set()
    memo_unreachable = set()

    # --- UI and Statistics Initialization ---
    console = Console()
    stats = ReplayStatistics(time_budget)
    print_header(console, header_title, ocel_name, time_budget, config)

    # --- Main Loop with Live Display ---
    with Live(
        stats.get_live_layout(),
        console=console,
        screen=False,
        refresh_per_second=4,
        vertical_overflow="visible",
    ) as live:
        while stats.passed_time < time_budget:
            iter_start_time = time.time()

            # Perform play-out
            (valid_sequences_iter, id_to_activity, id_to_object_type) = (
                playout_occn_extensive(occn, objects, parameters=parameters)
            )

            # Perform replay
            failed_replays, successful_replays = _perform_replay_on_ocpn(
                playout_mode,
                ocpn,
                ocpn_initial_marking,
                ocpn_final_marking,
                valid_sequences_iter,
                id_to_activity,
                id_to_object_type,
                memo_reachable=memo_reachable,
                memo_unreachable=memo_unreachable,
                precomputed=precomputed,
            )
            no_sequences = failed_replays + successful_replays

            # Update statistics and refresh the live display
            iter_time = time.time() - iter_start_time
            stats.update(no_sequences, failed_replays, iter_time)
            live.update(stats.get_live_layout())

    # --- Footer ---
    print_footer(console)


def _perform_replay_on_ocpn(
    playout_mode,
    ocpn,
    initial_marking,
    final_marking,
    sequences_iter,
    id_to_activity,
    id_to_object_type,
    memo_reachable=None,
    memo_unreachable=None,
    precomputed=None,
):
    """
    Performs replay on the OCPetriNet based on the specified playout mode.

    Returns
    -------
    tuple
        A tuple containing (failed_replays, successful_replays).
    """
    if playout_mode == "occn_replay_on_original_ocpn":
        return replay_on_original_ocpn(
            ocpn,
            initial_marking,
            final_marking,
            sequences_iter,
            id_to_activity,
            id_to_object_type,
        )
    elif playout_mode == "occn_replay_on_converted_ocpn":
        assert precomputed is not None, "Precomputed parameters are required for this playout mode."
        assert memo_reachable is not None, "Memoization for reachable places is required for this playout mode."
        assert memo_unreachable is not None, "Memoization for unreachable places is required for this playout mode."
        failed_replays, successful_replays = replay_on_converted_ocpn(
            ocpn,
            initial_marking,
            final_marking,
            sequences_iter,
            id_to_activity,
            id_to_object_type,
            memo_reachable,
            memo_unreachable,
            precomputed=precomputed,
        )
        return failed_replays, successful_replays
    else:
        raise ValueError(f"Unknown playout_mode provided: {playout_mode}")


def replay_on_converted_occn(occn, traces, idx_to_transition, id_to_obj_type):
    """
    Replay the given traces from the original OCPN on the converted OCCN.

    Parameters
    ----------
    occn : OCCausalNet
        The OCCausalNet object to replay the traces on.
    traces : list of list of tuples
        The traces to replay
    idx_to_transition : dict
        A mapping from transition indices to transition objects in the OCPN.
    id_to_obj_type : dict
        A mapping from object IDs to their respective object types.

    Returns
    -------
    int
        The number of failed replays.
    """
    failed_replays = 0
    for trace in traces:
        # convert transition indices to labels and
        # convert frozenset of object ids to mapping of object type to set of object ids
        trace_list = []
        for event in trace:
            # convert objects
            objects = defaultdict(set)
            for obj_id in event[1]:
                obj_type = id_to_obj_type[obj_id]
                objects[obj_type].add(obj_id)

            # convert transition index to label
            trace_list.append((idx_to_transition[event[0]].name, dict(objects)))

        trace = tuple(trace_list)

        # replay the trace on OCCN
        if not ConvertedOCCausalNetSemantics.replay(occn, trace):
            failed_replays += 1

    return failed_replays

def replay_on_original_occn(occn, traces, idx_to_transition, id_to_obj_type, precomputed):
    """
    Replay the given traces from the converted OCPN on the original OCCN.

    Parameters
    ----------
    occn : OCCausalNet
        The OCCausalNet object to replay the traces on.
    traces : list of list of tuples
        The traces to replay
    idx_to_transition : dict
        A mapping from transition indices to transition objects in the OCPN.
    id_to_obj_type : dict
        A mapping from object IDs to their respective object types.
    precomputed : dict
        Precomputed parameters for the replay.
    
    Returns
    -------
    int
        The number of failed replays.
    """
    failed_replays = 0
    
    # replay every trace
    for trace in traces:
        # Convert trace to corresponding OCCN sequence
        occn_sequence = ConvertedOCPetriNetSemantics.get_original_occn_trace(
            trace, idx_to_transition, id_to_obj_type, precomputed=precomputed
        )
        
        # Replay the OCCN sequence
        if not OCCausalNetSemantics.replay(occn, occn_sequence):
            failed_replays += 1

    return failed_replays


def replay_on_original_ocpn(
    ocpn,
    initial_marking,
    final_marking,
    valid_sequences_iter,
    id_to_activity,
    id_to_object_type,
):
    """
    Replay the given valid sequences of the transformed OCCN on the original OCPN.

    Parameters
    ----------
    ocpn : OCPetriNet
        The original OCPetriNet object to replay the traces on.
    initial_marking: OCMarking
        Initial marking to use for replay
    final_marking: OCMarking
        Final marking to use for replay
    valid_sequences_iter : iter of sequences where sequences are tuples of Binding objects
        The valid sequences to replay.
    id_to_activity : dict
        A mapping from activity IDs to their respective activity labels.
    id_to_object_type : dict
        A mapping from object IDs to their respective object types.

    Returns
    -------
    tuple
        A tuple containing:
            - int: The number of failed replays.
            - int: The number of successful replays.
    """
    failed_replays = 0
    successful_replays = 0

    for sequence in valid_sequences_iter:

        # Convert sequence to trace for the original ocpn
        trace = ConvertedOCCausalNetSemantics.get_original_ocpn_trace(
            ocpn, sequence, id_to_activity, id_to_object_type
        )

        if OCPetriNetSemantics.replay(ocpn, trace, initial_marking, final_marking):
            successful_replays += 1
        else:
            failed_replays += 1
    return failed_replays, successful_replays


def replay_on_converted_ocpn(
    ocpn,
    initial_marking,
    final_marking,
    sequences_iter,
    id_to_activity,
    id_to_object_type,
    memo_reachable,
    memo_unreachable,
    precomputed,
):
    """
    Replay the given valid sequences of an OCCN on the converted OCPN.
    Will allow any final marking that contains only tokens in the places
    specified by `final_marking`.

    Parameters
    ----------
    ocpn : OCPetriNet
        The converted OCPetriNet object to replay the traces on.
    initial_marking : OCMarking
        Initial marking to use for replay.
    final_marking : OCMarking
        Final marking to use for replay.
    sequences_iter : iter of sequences where sequences are tuples of Binding objects
        The valid sequences to replay.
    id_to_activity : dict
        A mapping from activity IDs to their respective activity labels.
    id_to_object_type : dict
        A mapping from object IDs to their respective object types.
    memo_reachable: set
        A set to memoize bindings that could be simulated successfully.
    memo_unreachable: set
        A set to memoize bindings that could not be simulated successfully.
    precomputed : dict
        Precomputed parameters for the replay.

    Returns
    -------
    tuple
        A tuple containing:
            - int: The number of failed replays.
            - int: The number of successful replays.
    """
    failed_replays = 0
    successful_replays = 0

    for sequence in sequences_iter:
        # Convert sequence to trace for the original ocpn
        if ConvertedOCPetriNetSemantics.replay_occn_sequence(
            sequence,
            initial_marking,
            final_marking,
            id_to_activity,
            id_to_object_type,
            memo_reachable,
            memo_unreachable,
            precomputed,
        ):
            successful_replays += 1
        else:
            failed_replays += 1

    return failed_replays, successful_replays


class ReplayStatistics:
    """A class to manage tracking and displaying replay statistics."""

    def __init__(self, time_budget):
        self.time_budget = time_budget
        self.start_time = time.time()
        self.passed_time = 0
        self.i = 0
        self.total_traces_generated = 0
        self.total_failed_replays = 0
        self.iteration_times = []
        self.traces_per_iteration = []

    def update(self, num_traces_in_iter, failed_replays, iter_time):
        """Update statistics after an iteration."""
        self.i += 1
        self.iteration_times.append(iter_time)
        self.traces_per_iteration.append(num_traces_in_iter)
        self.total_traces_generated += num_traces_in_iter
        self.total_failed_replays += failed_replays
        self.passed_time = time.time() - self.start_time

    def get_live_layout(self) -> Table:
        """Generates a side-by-side layout for live statistics."""
        layout_grid = Table.grid(expand=True)
        layout_grid.add_column(ratio=1)  # Left column
        layout_grid.add_column(ratio=1)  # Right column

        # --- Left Panel: Live Playout & Replay Statistics ---
        live_stats_table = Table(
            title="Live Playout & Replay Statistics",
            border_style="blue",
            box=box.SQUARE,
        )
        live_stats_table.add_column("Metric", style="dim", width=25)
        live_stats_table.add_column("Value", justify="right")

        failure_rate = (
            (self.total_failed_replays / self.total_traces_generated * 100)
            if self.total_traces_generated > 0
            else 0
        )
        success_rate = 100 - failure_rate
        success_color = "green" if success_rate == 100 else "yellow"

        live_stats_table.add_row(
            "[bold]Successful Replays[/bold]",
            f"{self.total_traces_generated - self.total_failed_replays} / {self.total_traces_generated} [bold {success_color}]({success_rate:.2f}%)[/bold {success_color}]",
        )
        live_stats_table.add_row(
            "Passed Time", f"{self.passed_time:.2f}s / {self.time_budget}s"
        )
        live_stats_table.add_row(
            "Total Traces Generated", f"{self.total_traces_generated}"
        )
        live_stats_table.add_row("Iterations", f"{self.i}")

        # --- Right Panel: Iteration Statistics ---
        iter_stats_table = Table.grid(expand=True, padding=(0, 1))
        iter_stats_table.add_column("Metric", style="dim")
        iter_stats_table.add_column("Value", justify="right")

        if self.iteration_times:  # Only display if we have data
            iter_stats_table.add_row("[bold]Traces / Iteration[/bold]", "")
            iter_stats_table.add_row("  Min", f"{min(self.traces_per_iteration)}")
            iter_stats_table.add_row("  Max", f"{max(self.traces_per_iteration)}")
            iter_stats_table.add_row(
                "  Average", f"{statistics.mean(self.traces_per_iteration):.2f}"
            )
            iter_stats_table.add_row(
                "  Median", f"{statistics.median(self.traces_per_iteration):.2f}"
            )
            iter_stats_table.add_row()  # Spacer row
            iter_stats_table.add_row("[bold]Time / Iteration (s)[/bold]", "")
            iter_stats_table.add_row("  Min", f"{min(self.iteration_times):.2f}s")
            iter_stats_table.add_row("  Max", f"{max(self.iteration_times):.2f}s")
            iter_stats_table.add_row(
                "  Average", f"{statistics.mean(self.iteration_times):.2f}s"
            )
            iter_stats_table.add_row(
                "  Median", f"{statistics.median(self.iteration_times):.2f}s"
            )
        else:
            iter_stats_table.add_row("Waiting for first iteration...")

        iter_stats_panel = Panel(
            iter_stats_table,
            title="Iteration Statistics",
            border_style="yellow",
            box=box.SQUARE,
        )

        # Combine the two panels into the main grid
        layout_grid.add_row(live_stats_table, iter_stats_panel)
        return layout_grid


def print_header(console, title, ocel_name, time_budget, config):
    """Prints the initial configuration header."""
    # --- Main Title ---
    console.print()
    console.print(Rule(f"[bold magenta]{title}[/bold magenta]", style="magenta"))
    console.print()

    # --- Configuration Panel ---
    config_text = (
        f"[bold]OCEL:[/bold] [cyan]{ocel_name}[/cyan]\n"
        f"[bold]Time Budget:[/bold] [cyan]{time_budget}s[/cyan]\n"
        f"[bold]Initial Marking:[/bold] {config['initial_marking']}\n"
        f"[bold]Final Marking:[/bold] {config['final_marking']}\n"
        f"[bold]Playout Parameters:[/bold] {config['parameters']}"
    )
    header_panel = Panel(
        Align.center(config_text, vertical="top"),
        title="Configuration",
        border_style="green",
        padding=(1, 2),
    )
    console.print(header_panel)
    console.print()


def print_footer(console):
    console.print(Rule("[bold magenta]Finished[/bold magenta]", style="magenta"))


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
                [("c", "Container", (1, 1), 0), ("i", "Container", (1, 1), 0)],
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
        "i": {
            "img": [
                [("START_Container", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("e", "Container", (1, 1), 0)],
            ],
        },
        "e": {
            "img": [
                [("c", "Container", (1, 1), 0), ("i", "Container", (1, 1), 0)],
            ],
            "omg": [
                [("s", "Container", (1, 1), 0)],
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


if __name__ == "__main__":
    evaluation()



import re
import time
import pm4py
import os
from rich.console import Console
from rich.live import Live
from collections import Counter, defaultdict
from multiprocessing import Manager
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED


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
from pm4py.objects.ocpn.obj import OCMarking
from pm4py.objects.ocpn.semantics import OCPetriNetSemantics

from converted_occn_semantics import ConvertedOCCausalNetSemantics
from converted_ocpn_semantics import ConvertedOCPetriNetSemantics
from replay_statistics import ReplayStatistics
from playout_parameters import playout_parameters
from running_ex import occn_running_ex, ocpn_running_ex
from container_logistics_occn import occn_container_logistics
from p2p_occn import occn_p2p, occn_p2p_small, occn_p2p_smaller

LOG_DIR = "evaluation/logs"

# Number of concurrent processes to use for the evaluation
NUM_PROCESSES = 1


def evaluation():
    """
    Main function to define and execute the evaluation plan.

    4 Variants are defined:
    - Discover OCPN, convert to OCCN, play-out on the original OCPN and replay on the converted OCCN. ("playout_ocpn_replay_on_converted_occn")
    - Discover OCPN, convert to OCCN, play-out on the converted OCCN and replay on the original OCPN. ("playout_converted_occn_replay_on_ocpn")
    - Discover OCCN, convert to OCPN, play-out on the original OCCN and replay on the converted OCPN. ("playout_occn_replay_on_converted_ocpn")
    - Discover OCCN, convert to OCPN, play-out on the converted OCPN and replay on the original OCCN. ("playout_ocpn_replay_on_original_occn")
    """
    # Each dictionary specifies the OCEL and the variants to run with their
    # respective configurations.
    evaluation_plan = [
        {
            "ocel_name": "ContainerLogistics.json",
            "variants_to_run": {
                "playout_ocpn_replay_on_original_occn": { 
                    "config_id": 4,
                    "time_budget": 14 * 60 * 60,
                }
            },
        },
    ]

    run_evaluation_plan(evaluation_plan)


def run_evaluation_plan(plan):
    """
    Parses and executes an evaluation plan.

    For each entry in the plan, this function determines which high-level
    evaluation function (eval_ocpn or eval_occn) to call based on the
    specified variants.

    Parameters
    ----------
    plan : list of dict
        A list of configuration dictionaries, where each dictionary defines
        the work for one OCEL.
    """
    # Define which variants belong to which discovery method
    ocpn_discovery_variants = {
        "playout_ocpn_replay_on_converted_occn",
        "playout_converted_occn_replay_on_ocpn",
    }
    occn_discovery_variants = {
        "playout_occn_replay_on_converted_ocpn",
        "playout_ocpn_replay_on_original_occn",
    }

    for config in plan:
        ocel_name = config["ocel_name"]
        variants_to_run = config["variants_to_run"]

        # Filter params for the OCPN discovery path
        params_for_ocpn = {
            k: v for k, v in variants_to_run.items() if k in ocpn_discovery_variants
        }
        if params_for_ocpn:
            eval_ocpn(ocel_name, params_for_ocpn)

        # Filter params for the OCCN discovery path
        params_for_occn = {
            k: v for k, v in variants_to_run.items() if k in occn_discovery_variants
        }
        if params_for_occn:
            eval_occn(ocel_name, params_for_occn)


def eval_ocpn(ocel_name, variant_params):
    """
    Discover an OCPN, convert it to OCCN, and perform play-out/replay.

    This function conditionally executes one or both of its evaluation
    variants based on the provided parameters.

    Parameters
    ----------
    ocel_name : str
        Name of the OCEL to evaluate.
    variant_params : dict
        A dictionary where keys are the names of the variants to run and
        values are dictionaries containing the 'config_id' and 'time_budget'.
    """
    # Discover OCPN
    if ocel_name == "running_ex":
        ocpn = ocpn_running_ex()
    else:
        ocpn = discover_ocpn(ocel_name)

    # Convert to OCCausalNet object
    occn = ocpn_converter.apply(ocpn, variant=ocpn_converter.Variants.TO_OC_CAUSAL_NET)

    # Variant 1: Playout OCPN and replay on converted OCCN
    if "playout_ocpn_replay_on_converted_occn" in variant_params:
        params = variant_params["playout_ocpn_replay_on_converted_occn"]
        playout_ocpn_replay_on_converted_occn(
            ocpn,
            occn,
            ocel_name,
            time_budget=params["time_budget"],
            config_id=params["config_id"],
        )

    # Variant 2: Playout converted OCCN and replay on original OCPN
    if "playout_converted_occn_replay_on_ocpn" in variant_params:
        params = variant_params["playout_converted_occn_replay_on_ocpn"]
        playout_converted_occn_replay_on_ocpn(
            ocpn,
            occn,
            ocel_name,
            time_budget=params["time_budget"],
            config_id=params["config_id"],
        )


def eval_occn(ocel_name, variant_params):
    """
    Discover an OCCN, convert it to OCPN, and perform play-out/replay.

    This function conditionally executes one or both of its evaluation
    variants based on the provided parameters.

    Parameters
    ----------
    ocel_name : str
        Name of the OCEL to evaluate.
    variant_params : dict
        A dictionary where keys are the names of the variants to run and
        values are dictionaries containing the 'config_id' and 'time_budget'.
    """
    # Discover OCCN
    occn = discover_occn(ocel_name)

    # Convert to OCPetriNet object
    ocpn = occn_converter.apply(occn, variant=occn_converter.Variants.TO_OCPN)
    _save_viz_ocpn_converted(ocpn, ocel_name)

    # Variant 1: Playout OCCN and replay on converted OCPN
    if "playout_occn_replay_on_converted_ocpn" in variant_params:
        params = variant_params["playout_occn_replay_on_converted_ocpn"]
        playout_occn_replay_on_converted_ocpn(
            occn,
            ocpn,
            ocel_name,
            time_budget=params["time_budget"],
            config_id=params["config_id"],
        )

    # Variant 2: Playout converted OCPN and replay on original OCCN
    if "playout_ocpn_replay_on_original_occn" in variant_params:
        params = variant_params["playout_ocpn_replay_on_original_occn"]
        playout_ocpn_replay_on_original_occn(
            ocpn,
            occn,
            ocel_name,
            time_budget=params["time_budget"],
            config_id=params["config_id"],
        )


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
    This function reads the OCEL and discovers the OCCausalNet.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file (e.g., "ContainerLogistics.json").

    Returns
    -------
    OCCausalNet
        The discovered OCCausalNet object.
    """
    if ocel_name == "running_ex":
        occn = occn_running_ex()
    elif ocel_name == "ContainerLogistics.json":
        occn = occn_container_logistics()
    elif ocel_name == "ocel2-p2p.json":
        occn = occn_p2p()
    elif ocel_name == "ocel2-p2p-small.json":
        occn = occn_p2p_small()
    elif ocel_name == "ocel2-p2p-smaller.json":
        occn = occn_p2p_smaller()
    else:
        raise ValueError(f"Unknown OCCN for OCEL name: {ocel_name}")

    return occn


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
        assert (
            precomputed is not None
        ), "Precomputed parameters are required for this playout mode."

        # Add binding token to both markings
        global_binding_place = precomputed["global_binding_place"]
        initial_marking = ConvertedOCPetriNetSemantics._add_binding_token(
            initial_marking, global_binding_place
        )
        final_marking = ConvertedOCPetriNetSemantics._add_binding_token(
            final_marking, global_binding_place
        )

    parameters = config["parameters"]

    # --- UI and Statistics Initialization ---
    console = Console()
    stats = ReplayStatistics(time_budget, NUM_PROCESSES, log_dir=LOG_DIR)
    stats.print_header(
        console,
        header_title,
        ocel_name,
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

        # Manage processes
        executor = ProcessPoolExecutor(max_workers=NUM_PROCESSES)
        active_futures = set()

        # Fill worker pool with initial tasks
        for _ in range(NUM_PROCESSES):
            future = executor.submit(
                _run_single_ocpn_playout_and_replay_on_occn_iteration,
                ocpn,
                initial_marking,
                final_marking,
                parameters,
                playout_mode,
                occn,
                precomputed,
            )
            active_futures.add(future)

        # As long as there is time left, restart any completed task
        while active_futures and stats.passed_time < time_budget:
            # Wait for any task to complete
            done_futures, _ = wait(active_futures, return_when=FIRST_COMPLETED)

            for future in done_futures:
                # Process result: update stats
                num_traces, failed_replays, iter_time = future.result()
                stats.update(num_traces, failed_replays, iter_time)
                live.update(stats.get_live_layout())

                # Remove completed future from the set
                active_futures.remove(future)

                # Restart task if time budget allows
                if stats.passed_time < time_budget:
                    new_future = executor.submit(
                        _run_single_ocpn_playout_and_replay_on_occn_iteration,
                        ocpn,
                        initial_marking,
                        final_marking,
                        parameters,
                        playout_mode,
                        occn,
                        precomputed,
                    )
                    active_futures.add(new_future)

        # Time budget is exceeded, cancel all remaining tasks
        executor.shutdown(wait=False, cancel_futures=True)

    # --- Footer ---
    stats.print_footer(console)


def _run_single_ocpn_playout_and_replay_on_occn_iteration(
    ocpn, initial_marking, final_marking, parameters, playout_mode, occn, precomputed
):
    """
    Executes one iteration of play-out and replay. This function is run by each process.
    """
    iter_start_time = time.time()

    # Perform play-out
    (traces, idx_to_transition, id_to_obj_type) = playout_ocpn_extensive(
        ocpn, initial_marking, final_marking, parameters=parameters
    )

    # Perform replay
    failed_replays = _perform_replay_on_occn(
        playout_mode,
        occn,
        traces,
        idx_to_transition,
        id_to_obj_type,
        precomputed=precomputed,
    )

    iter_time = time.time() - iter_start_time

    # Return results needed for stats.update()
    return (len(traces), failed_replays, iter_time)


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
        return replay_on_original_occn(
            occn, traces, idx_to_transition, id_to_obj_type, precomputed=precomputed
        )
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

    # --- UI and Statistics Initialization ---
    console = Console()
    stats = ReplayStatistics(time_budget, NUM_PROCESSES, log_dir=LOG_DIR)
    stats.print_header(console, header_title, ocel_name, config)

    # --- Main Loop with Live Display ---
    with Live(
        stats.get_live_layout(),
        console=console,
        screen=False,
        refresh_per_second=4,
        vertical_overflow="visible",
    ) as live:
        
        with Manager() as manager:
            # use manager to create shared memoization dictionaries
            # (only used for playout mode "occn_replay_on_converted_ocpn")
            memo_reachable = manager.dict()
            memo_unreachable = manager.dict()
            
            # Fill worker pool with initial tasks
            executor = ProcessPoolExecutor(max_workers=NUM_PROCESSES)
            active_futures = set()
            
            for _ in range(NUM_PROCESSES):
                future = executor.submit(
                    _run_single_occn_playout_and_replay_on_ocpn_iteration,
                    occn,
                    objects,
                    parameters,
                    playout_mode,
                    ocpn,
                    ocpn_initial_marking,
                    ocpn_final_marking,
                    memo_reachable,  
                    memo_unreachable,
                    precomputed,
                )
                active_futures.add(future)
                
            # As long as there is time left, restart any completed task
            while active_futures and stats.passed_time < time_budget:
                # Wait for the first process to finish its task
                done_futures, _ = wait(active_futures, return_when=FIRST_COMPLETED)
                
                for future in done_futures:
                    # Collect results and update statistics
                    num_sequences, failed_replays, iter_time = future.result()
                    stats.update(num_sequences, failed_replays, iter_time)
                    live.update(stats.get_live_layout())

                    active_futures.remove(future)

                    # If the time budget allows, submit a new task to replace the one that just finished
                    if stats.passed_time < time_budget:
                        new_future = executor.submit(
                            _run_single_occn_playout_and_replay_on_ocpn_iteration,
                            occn,
                            objects,
                            parameters,
                            playout_mode,
                            ocpn,
                            ocpn_initial_marking,
                            ocpn_final_marking,
                            memo_reachable,
                            memo_unreachable,
                            precomputed,
                        )
                        active_futures.add(new_future)
            
            # Time budget is exceeded, cancel all remaining tasks
            executor.shutdown(wait=False, cancel_futures=True)

    # --- Footer ---
    stats.print_footer(console)
    
def _run_single_occn_playout_and_replay_on_ocpn_iteration(
    occn,
    objects,
    parameters,
    playout_mode,
    ocpn,
    ocpn_initial_marking,
    ocpn_final_marking,
    memo_reachable,
    memo_unreachable,
    precomputed,
):
    """
    Executes one iteration of OCCN play-out and OCPN replay.
    This function is run by each independent process and communicates with the
    central Manager to read from and write to the shared memoization sets.
    """
    iter_start_time = time.time()

    # Perform play-out
    (valid_sequences_iter, id_to_activity, id_to_object_type) = playout_occn_extensive(
        occn, objects, parameters=parameters
    )

    # Perform replay
    # The replay function uses the shared memoization dictionaries (proxies) for its checks.
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

    iter_time = time.time() - iter_start_time
    return (no_sequences, failed_replays, iter_time)


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
        assert (
            precomputed is not None
        ), "Precomputed parameters are required for this playout mode."
        assert (
            memo_reachable is not None
        ), "Memoization for reachable places is required for this playout mode."
        assert (
            memo_unreachable is not None
        ), "Memoization for unreachable places is required for this playout mode."
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


def replay_on_original_occn(
    occn, traces, idx_to_transition, id_to_obj_type, precomputed
):
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
    memo_reachable: dict
        A dict to memoize bindings that could be simulated successfully.
    memo_unreachable: dict
        A dict to memoize bindings that could not be simulated successfully.
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


def _save_viz_ocpn_converted(ocpn, ocel_name):
    """
    Transforms the OCPetriNet to the alternate format and saves a visualization.

    Parameters
    ----------
    ocpn : OCPetriNet
        The OCPetriNet object to visualize.
    ocel_name : str
        The name of the OCEL file, used for naming the visualization file.
    """
    # convert to alternate format
    alternate_ocpn = ocpn_converter.apply(
        ocpn, variant=ocpn_converter.Variants.TO_ALTERNATIVE_FORMAT
    )

    # create converted_ocpns directory if it doesn't exist
    if not os.path.exists("evaluation/converted_ocpns"):
        os.makedirs("evaluation/converted_ocpns")
    # Save visualization
    path_png = os.path.join("evaluation", "converted_ocpns", f"{ocel_name}.png")
    pm4py.save_vis_ocpn(alternate_ocpn, path_png)


if __name__ == "__main__":
    evaluation()

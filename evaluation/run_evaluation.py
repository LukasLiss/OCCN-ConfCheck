from collections import Counter, defaultdict
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
from pm4py.objects.ocpn import factory as ocpn_factory
from pm4py.objects.ocpn import converter as ocpn_converter
from pm4py.algo.simulation.playout.ocpn.variants.extensive import (
    apply as playout_ocpn_extensive,
)
from pm4py.objects.ocpn.obj import OCMarking

DEFAULT_MAX_BINDINGS_PER_ACTIVITY = 3

def evaluation():
    ocels = ["ContainerLogistics.json"]
    time_budget = 60*60  # seconds

    for ocel_name in ocels:

        # Discover OCPN
        ocpn = discover_ocpn(ocel_name)

        # Convert to OCCausalNet object
        occn = ocpn_converter.apply(
            ocpn, variant=ocpn_converter.Variants.TO_OC_CAUSAL_NET
        )

        # Playout OCPN and replay on OCCN
        playout_ocpn_replay_on_occn(ocpn, occn, ocel_name, time_budget)

def ocpn_playout_parameters(ocel_name, config_id=0):
    """
    Specifies parameters for OCPN play-out based on the OCEL name and configuration ID.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file.
    config_id : int, optional
        The configuration ID (default is 0).

    Returns
    -------
    dict
        A dictionary with parameters for the OCPN play-out.
            - "object_numbers": A dictionary mapping object types to their respective counts in the initial marking.
            - "parameters": dictionary
                - "branchingFactorTransitions": The branching factor for transitions.
                - "branchingFactorBindings": The branching factor for bindings.
                - "maxBindingsPerActivity": The maximum number of bindings per activity.
    """
    if ocel_name == "ContainerLogistics.json":
        if config_id == 0:  # smallest example
            branching_factor = 1.4
            max_bindings_per_activity = DEFAULT_MAX_BINDINGS_PER_ACTIVITY
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
            branching_factor = 1.2
            max_bindings_per_activity = DEFAULT_MAX_BINDINGS_PER_ACTIVITY
            object_numbers = {
                "Customer Order": 2,
                "Transport Document": 2,
                "Vehicle": 1,
                "Container": 4,
                "Truck": 1,
                "Handling Unit": 4,
                "Forklift": 1,
            }

    return {
        "parameters": {
            "branchingFactorTransitions": branching_factor,
            "branchingFactorBindings": branching_factor,
            "return_traces": True
        },
        "maxBindingsPerActivity": max_bindings_per_activity,
        "object_numbers": object_numbers,
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


def ocpn_playout_config(ocel_name, ocpn, config_id=0):
    """
    This function returns the configuration for the OCPN play-out based on the OCEL name and config ID.

    Parameters
    ----------
    ocel_name : str
        The name of the OCEL file.
    ocpn : OCPetriNet
        The OCPetriNet object.
    config_id : int, optional
        The configuration ID (default is 0).

    Returns
    -------
    dict
        The configuration dictionary for the OCPN play-out.
            - "initial_marking": The initial marking of the OCPN.
            - "final_marking": The final marking of the OCPN.
            - "parameters": The parameters for the play-out algorithm.
    """
    ocel_params = ocpn_playout_parameters(ocel_name, config_id)

    # get source & target places of the ocpn
    source_places = {}
    sink_places = {}
    for place in ocpn.places:
        if place.name.endswith("source"):
            source_places[place.object_type] = place
        elif place.name.endswith("sink"):
            sink_places[place.object_type] = place

    # get initial and final markings
    initial_marking = {
        source_places[obj_type]: Counter(
            [f"{obj_type}_{i}" for i in range(obj_count)] 
        )
        for obj_type, obj_count in ocel_params["object_numbers"].items()
    }

    final_marking = {
        sink_places[obj_type]: Counter(
            [f"{obj_type}_{i}" for i in range(obj_count)]
        )
        for obj_type, obj_count in ocel_params["object_numbers"].items()
    }
    
    return {
        "initial_marking": OCMarking(initial_marking),
        "final_marking": OCMarking(final_marking),
        "parameters": ocel_params["parameters"],
    }
    
def playout_ocpn_replay_on_occn(ocpn, occn, ocel_name, time_budget):
    """
    Generate random traces from the OCPN and replay them on the OCCN.
    
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
    # --- Configuration Setup ---
    config = ocpn_playout_config(ocel_name, ocpn)
    initial_marking = OCMarking(config["initial_marking"])
    final_marking = OCMarking(config["final_marking"])
    parameters = config["parameters"]

    # --- UI and Statistics Initialization ---
    console = Console()
    stats = ReplayStatistics(time_budget)
    print_header(console, ocel_name, time_budget, config)

    # --- Main Loop with Live Display ---
    with Live(stats.get_live_layout(), console=console, screen=False, refresh_per_second=4, vertical_overflow="visible") as live:
        while stats.passed_time < time_budget:
            iter_start_time = time.time()

            # Perform play-out
            (traces, idx_to_transition, id_to_obj_type) = playout_ocpn_extensive(
                ocpn, initial_marking, final_marking, parameters=parameters
            )

            # Try to replay the traces on the OCCN
            failed_replays = replay_on_converted_occn(occn, traces, idx_to_transition, id_to_obj_type)

            # Update statistics and refresh the live display
            iter_time = time.time() - iter_start_time
            stats.update(len(traces), failed_replays, iter_time)
            live.update(stats.get_live_layout())

    # --- Footer ---
    print_footer(console)
    
    
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
            box=box.SQUARE
        )
        live_stats_table.add_column("Metric", style="dim", width=25)
        live_stats_table.add_column("Value", justify="right")

        failure_rate = (self.total_failed_replays / self.total_traces_generated * 100) if self.total_traces_generated > 0 else 0
        success_rate = 100 - failure_rate
        success_color = "green" if success_rate == 100 else "yellow"
        
        live_stats_table.add_row("[bold]Successful Replays[/bold]", f"{self.total_traces_generated - self.total_failed_replays} / {self.total_traces_generated} [bold {success_color}]({success_rate:.2f}%)[/bold {success_color}]")
        live_stats_table.add_row("Passed Time", f"{self.passed_time:.2f}s / {self.time_budget}s")
        live_stats_table.add_row("Total Traces Generated", f"{self.total_traces_generated}")
        live_stats_table.add_row("Iterations", f"{self.i}")

        # --- Right Panel: Iteration Statistics ---
        iter_stats_table = Table.grid(expand=True, padding=(0, 1))
        iter_stats_table.add_column("Metric", style="dim")
        iter_stats_table.add_column("Value", justify="right")

        if self.iteration_times:  # Only display if we have data
            iter_stats_table.add_row("[bold]Traces / Iteration[/bold]", "")
            iter_stats_table.add_row("  Min", f"{min(self.traces_per_iteration)}")
            iter_stats_table.add_row("  Max", f"{max(self.traces_per_iteration)}")
            iter_stats_table.add_row("  Average", f"{statistics.mean(self.traces_per_iteration):.2f}")
            iter_stats_table.add_row("  Median", f"{statistics.median(self.traces_per_iteration):.2f}")
            iter_stats_table.add_row()  # Spacer row
            iter_stats_table.add_row("[bold]Time / Iteration (s)[/bold]", "")
            iter_stats_table.add_row("  Min", f"{min(self.iteration_times):.2f}s")
            iter_stats_table.add_row("  Max", f"{max(self.iteration_times):.2f}s")
            iter_stats_table.add_row("  Average", f"{statistics.mean(self.iteration_times):.2f}s")
            iter_stats_table.add_row("  Median", f"{statistics.median(self.iteration_times):.2f}s")
        else:
            iter_stats_table.add_row("Waiting for first iteration...")

        iter_stats_panel = Panel(
            iter_stats_table,
            title="Iteration Statistics",
            border_style="yellow",
            box=box.SQUARE
        )
        
        # Combine the two panels into the main grid
        layout_grid.add_row(live_stats_table, iter_stats_panel)
        return layout_grid


def print_header(console, ocel_name, time_budget, config):
    """Prints the initial configuration header."""
    # --- Main Title ---
    console.print() 
    console.print(Rule("[bold magenta]OCPN Playout & Replay on OCCN[/bold magenta]", style="magenta"))
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
        padding=(1, 2)
    )
    console.print(header_panel)
    console.print()

def print_footer(console):
    console.print(Rule("[bold magenta]Finished[/bold magenta]", style="magenta"))

if __name__ == "__main__":
    evaluation()

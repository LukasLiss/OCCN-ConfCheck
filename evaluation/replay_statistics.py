import statistics
import time
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.align import Align
from rich import box

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
# dashboard.py
import os
import json
import time
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from rich.console import Console
from rich.align import Align

console = Console()
stats_file = 'stats.json'

def load_stats():
    """Loads the IPC stats.json file from the mitmproxy addon"""
    if not os.path.exists(stats_file):
        return {
            'active_sessions': 0,
            'total_queries': 0,
            'total_dummies': 0,
            'total_original_bytes': 0,
            'total_dummy_bytes': 0,
            'history': []
        }
    try:
        with open(stats_file, 'r') as f:
            return json.load(f)
    except Exception:
        # Fallback in case of temporary read collisions
        time.sleep(0.05)
        try:
            with open(stats_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                'active_sessions': 0,
                'total_queries': 0,
                'total_dummies': 0,
                'total_original_bytes': 0,
                'total_dummy_bytes': 0,
                'history': []
            }

def make_header() -> Panel:
    """Renders the top panel header"""
    title = "[bold green]🛡️ D O H - S H I E L D[/bold green] [white]— Real-Time Traffic Morphing Proxy[/white]"
    subtitle = "[cyan]CS362IA: Network Programming and Security | Semester VI | RVCE[/cyan]"
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_row(title)
    grid.add_row(subtitle)
    return Panel(grid, style="bold blue", box=box.ROUNDED)

def make_footer() -> Panel:
    """Renders the bottom panel footer with the DP bound formula"""
    formula = "Formal Attacker Bound: [bold yellow]P(attack) <= 1/k_min + e^(-ε)[/bold yellow] | [cyan]k_min = 343, ε = 1.0 (Target Attacker Bound <= 37.08%)[/cyan]"
    align = Align.center(formula)
    return Panel(align, style="bold cyan", box=box.ROUNDED)

def make_stats_panel(stats) -> Panel:
    """Renders the side stats panel"""
    table = Table(show_header=False, expand=True, box=None)
    table.add_column("Metric", style="bold white", width=22)
    table.add_column("Value", style="bold green", justify="right")
    
    table.add_row("Active Connections", f"[cyan]{stats['active_sessions']}[/cyan]")
    table.add_row("Total Intercepted", f"{stats['total_queries']}")
    table.add_row("Dummy Injected", f"[yellow]{stats['total_dummies']}[/yellow]")
    
    # Bytes formatting
    orig_kb = stats['total_original_bytes'] / 1024.0
    dummy_kb = stats['total_dummy_bytes'] / 1024.0
    table.add_row("Original Data", f"{orig_kb:.1f} KB")
    table.add_row("Obfuscation Data", f"[yellow]{dummy_kb:.1f} KB[/yellow]")
    
    # Cumulative bandwidth overhead
    cum_overhead = (stats['total_dummy_bytes'] / stats['total_original_bytes'] * 100.0) if stats['total_original_bytes'] > 0 else 0.0
    table.add_row("Bandwidth Overhead", f"[bold red]{cum_overhead:.1f}%[/bold red]")
    
    # Active privacy budget
    table.add_row("Privacy Budget (ε)", "[bold green]1.0[/bold green]")
    table.add_row("Target Privacy Level", "[bold yellow]37.08%[/bold yellow]")
    
    return Panel(table, title="[bold white]Proxy Metrics[/bold white]", border_style="green", box=box.ROUNDED)

def make_history_table(stats) -> Panel:
    """Renders the central flow history table"""
    table = Table(expand=True, box=box.SIMPLE)
    table.add_column("Time", style="dim white", width=10)
    table.add_column("Requested Domain", style="bold cyan", ratio=3)
    table.add_column("Queries", justify="center", style="white")
    table.add_column("Original Data", justify="right", style="white")
    table.add_column("Target Cluster", justify="center", style="magenta")
    table.add_column("Dummies Injected", justify="center", style="yellow")
    table.add_column("BW Overhead", justify="right", style="red")
    table.add_column("DP Bound", justify="right", style="green")
    
    history = stats.get('history', [])
    # Render in reverse order to see new events at top of list
    for item in reversed(history):
        table.add_row(
            item['timestamp'],
            item['domain'],
            str(item['queries']),
            f"{item['original_bytes'] / 1024.0:.1f} KB",
            f"Cluster {item['target_cluster']}",
            f"+{item['dummies_injected']} ({item['dummy_size']}B)",
            f"{item['overhead_pct']:.1f}%",
            f"{item['privacy_bound']:.2f}%"
        )
        
    return Panel(table, title="[bold white]Morphed Website Flow History (Idle Time Triggered)[/bold white]", border_style="blue", box=box.ROUNDED)

def main():
    # Set terminal title
    print("\033]0;🛡️ DoH-Shield Dashboard\007", end="")
    
    layout = Layout()
    layout.split(
        Layout(name="header", size=4),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="stats", ratio=1),
        Layout(name="history", ratio=3)
    )
    
    os.system('clear')
    
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            stats = load_stats()
            layout["header"].update(make_header())
            layout["footer"].update(make_footer())
            layout["stats"].update(make_stats_panel(stats))
            layout["history"].update(make_history_table(stats))
            time.sleep(0.25)

if __name__ == "__main__":
    main()

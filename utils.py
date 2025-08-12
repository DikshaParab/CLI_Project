from rich.console import Console
from rich.text import Text

console = Console()

def clear_screen():
    """Clear terminal screen"""
    print("\033c", end="")

def display_header(title):
    """Display styled header"""
    console.print(
        Text(title, style="bold blue"),
        justify="center"
    )
    console.print("=" * len(title), justify="center")
    print()

def print_success(message):
    """Print success message"""
    console.print(f"[green] {message}")

def print_error(message):
    """Print error message"""
    console.print(f"[red] {message}")

def print_warning(message):
    """Print warning message"""
    console.print(f"[yellow]! {message}")

def print_info(message):
    """Print info message"""
    console.print(f"[blue]→ {message}")
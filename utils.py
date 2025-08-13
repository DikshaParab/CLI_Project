from rich.console import Console
from rich.text import Text

console = Console()

def clear_screen():
    print("\033c", end="")

def display_header(title):
    console.print(
        Text(title, style="bold blue"),
        justify="left"
    )
    console.print("=" * len(title), justify="left")
    print()

def print_success(message):
    console.print(f"[green] {message}")

def print_error(message):
    console.print(f"[red] {message}")

def print_warning(message):
    console.print(f"[yellow]! {message}")

def print_info(message):
    console.print(f"[blue] {message}")
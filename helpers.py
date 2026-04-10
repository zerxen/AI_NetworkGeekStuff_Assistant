"""Helper utilities for the project."""

import os
from config import DEBUG_MODE

# Enable ANSI escape codes in Windows CMD
os.system("")

# ANSI color codes
class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[96m"    # LLM response
    YELLOW  = "\033[93m"    # Tokens / info / tool name
    GRAY    = "\033[90m"    # Debug output
    GREEN   = "\033[92m"    # User prompt label
    RED     = "\033[91m"    # Errors
    PINK    = "\033[95m"    # Tool parameters (magenta/pink)
    PURPLE  = "\033[35m"    # Tool output (light purple)


def tool_call_print(name: str, arguments: dict):
    """Print tool name in yellow and its parameters in pink."""
    print(f"{Colors.BOLD}{Colors.YELLOW}>> Tool: {name}{Colors.RESET}")
    for k, v in arguments.items():
        print(f"   {Colors.PINK}{k}{Colors.RESET} = {Colors.PINK}{v}{Colors.RESET}")


def tool_result_print(name: str, result: str):
    """Print tool output in light purple."""
    # Truncate very long outputs for readability
    display = result if len(result) <= 500 else result[:500] + "…"
    print(f"   {Colors.PURPLE}<< [{name}] {display}{Colors.RESET}")


def llm_print(text: str):
    """Print LLM response in bold cyan so it stands out from debug output."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}LLM:{Colors.RESET} {Colors.CYAN}{text}{Colors.RESET}")


def info_print(label: str, value):
    """Print an info line (e.g. token counts) in yellow."""
    print(f"{Colors.YELLOW}{label}{Colors.RESET}", value)


def debug_print(*args, **kwargs):
    """
    Conditional debug print function that respects the DEBUG_MODE setting.

    Only prints if DEBUG_MODE is enabled in config.py.
    """
    if DEBUG_MODE:
        # Wrap debug output in gray so it fades into the background
        print(f"{Colors.GRAY}", end="")
        print(*args, **kwargs)
        print(f"{Colors.RESET}", end="", flush=True)

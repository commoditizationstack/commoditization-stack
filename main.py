#!/usr/bin/env python3
"""Interactive launcher for commoditization-stack-simulation.

Run this from VSCode (F5 → "Main menu") or from the terminal:

    python main.py            # opens the menu
    python main.py 1          # runs option 1 directly (skip the menu)
    python main.py --list     # lists all options and exits

Every option below delegates to a script under scripts/, to pytest, or
to streamlit. Parameters live in config/parameters.yaml.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
PY = sys.executable  # works whether run inside .venv or system Python


def run(cmd: List[str]) -> int:
    """Run a subprocess in the project root, streaming stdout/stderr live."""
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(f"\n$ {pretty}\n", flush=True)
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


# ----------------------------------------------------------------------------
# Actions
# ----------------------------------------------------------------------------

def action_streamlit() -> int:
    return run([PY, "-m", "streamlit", "run", "app/streamlit_app.py"])


def action_pytest() -> int:
    return run([PY, "-m", "pytest", "tests/", "-v"])


def action_script(name: str) -> Callable[[], int]:
    def _run() -> int:
        return run([PY, f"scripts/{name}"])
    return _run


def action_run_all_paper_figures() -> int:
    """Sequence: every paper figure from Sections 4–8 and Appendices A–G."""
    scripts = [
        "run_deterministic.py",
        "run_jurisdictional.py",
        "run_layer7.py",
        "run_appendix_a.py",
        "run_appendix_b.py",
        "run_section_7_5_migration.py",
        "run_appendix_d.py",
        "run_appendix_e.py",
        "run_appendix_f.py",
        "run_appendix_g.py",
        "render_equations.py",
    ]
    for s in scripts:
        rc = run([PY, f"scripts/{s}"])
        if rc != 0:
            print(f"\n[main.py] {s} exited with code {rc}. Stopping.")
            return rc
    print("\n[main.py] All paper figures regenerated in outputs/figures/ + outputs/tables/.")
    return 0


def action_monte_carlo() -> int:
    return run([PY, "scripts/run_monte_carlo.py"])


def action_notebooks() -> int:
    return run([PY, "-m", "jupyter", "lab", "notebooks/"])


def action_check_config() -> int:
    """Load config/parameters.yaml and print top-level sections."""
    return run([
        PY, "-c",
        "from src import config; "
        "p = config.load_parameters(); "
        "print('Loaded', len(p), 'sections from config/parameters.yaml:'); "
        "[print(' -', k) for k in p]"
    ])


# ----------------------------------------------------------------------------
# Menu definition
# ----------------------------------------------------------------------------

# (key, label, action). Order matters — these are the numbers shown to the user.
MENU: List[Tuple[str, str, Callable[[], int]]] = [
    ("1", "Streamlit app (interactive, http://localhost:8501)", action_streamlit),
    ("2", "Run all paper figures (every figure from Sections 4–8 + Appendices A–G)", action_run_all_paper_figures),
    ("3", "Monte Carlo ensemble (40k runs, ~30s)", action_monte_carlo),
    ("4", "Deterministic figures (fig1–fig7)", action_script("run_deterministic.py")),
    ("5", "Jurisdictional figures (fig11–fig13, Brazil/France/US)", action_script("run_jurisdictional.py")),
    ("6", "Layer 7 / K7 sensitivity (fig14, fig15)", action_script("run_layer7.py")),
    ("7", "Appendix A — layered DCF (fig16–fig18)", action_script("run_appendix_a.py")),
    ("8", "Appendix B — two-phase WACC/EVA (fig19, fig20)", action_script("run_appendix_b.py")),
    ("9", "Section 7.5 — Migration dynamics with AI orchestrator (fig21–fig23)", action_script("run_section_7_5_migration.py")),
    ("10", "Appendix D — Streaming case + fiscal blocs (fig24–fig30)", action_script("run_appendix_d.py")),
    ("11", "Appendix E — Dynamic case companies NC + DF (fig31–fig35)", action_script("run_appendix_e.py")),
    ("12", "Appendix F — Upstream chain + sensitivities (fig36–fig39)", action_script("run_appendix_f.py")),
    ("13", "Appendix G — Distributional + XAI capacity gap (fig40, fig41)", action_script("run_appendix_g.py")),
    ("14", "Render appendix equations (PNG)", action_script("render_equations.py")),
    ("15", "Run pytest test suite", action_pytest),
    ("16", "Open Jupyter Lab on notebooks/", action_notebooks),
    ("17", "Inspect parameters.yaml (list loaded sections)", action_check_config),
]


def print_menu() -> None:
    print()
    print("=" * 68)
    print(" commoditization-stack-simulation — interactive launcher")
    print("=" * 68)
    for key, label, _ in MENU:
        print(f"  {key:>2}) {label}")
    print(f"   q) Quit")
    print("=" * 68)
    print(" Parameters: config/parameters.yaml (edit, save, re-run)")
    print()


def find_action(key: str) -> Callable[[], int] | None:
    for k, _, action in MENU:
        if k == key:
            return action
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive launcher for commoditization-stack-simulation.",
    )
    parser.add_argument(
        "choice",
        nargs="?",
        help="Menu number to run directly (skip the prompt).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the menu and exit (no prompt).",
    )
    args = parser.parse_args()

    if args.list:
        print_menu()
        return 0

    if args.choice:
        action = find_action(args.choice)
        if action is None:
            print(f"[main.py] Unknown choice: {args.choice}")
            print_menu()
            return 2
        return action()

    while True:
        print_menu()
        try:
            choice = input("Choose [1-17, q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if choice in ("q", "quit", "exit"):
            return 0
        action = find_action(choice)
        if action is None:
            print(f"[main.py] '{choice}' is not a valid option.")
            continue
        rc = action()
        print(f"\n[main.py] Exit code: {rc}")
        again = input("\nReturn to menu? [Y/n]: ").strip().lower()
        if again in ("n", "no"):
            return rc


if __name__ == "__main__":
    sys.exit(main())

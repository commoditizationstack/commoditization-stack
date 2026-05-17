"""Named-scenario storage for the simulator session.

Each named scenario is a copy of the current overrides plus the list
of active jurisdictions, stored under ``st.session_state['scenarios']``
keyed by user-chosen name. Recall replaces the live overrides with the
snapshot; rename, duplicate and delete are first-class operations.

The store is session-local. To persist across sessions, save the
scenario as YAML via the existing 💾 Scenario YAML download in the
sidebar.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Dict, List

import streamlit as st


def _slot() -> Dict[str, Dict]:
    if "scenarios" not in st.session_state:
        st.session_state["scenarios"] = {}
    return st.session_state["scenarios"]


def list_names() -> List[str]:
    return list(_slot().keys())


def save(name: str) -> bool:
    """Snapshot current overrides + active countries under ``name``.

    Returns False if the name is empty or already taken (use rename or
    overwrite to replace).
    """
    name = (name or "").strip()
    if not name:
        return False
    slot = _slot()
    slot[name] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "overrides": deepcopy(st.session_state.get("overrides", {})),
        "countries": list(st.session_state.get("countries") or []),
    }
    return True


def overwrite(name: str) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    slot = _slot()
    slot[name] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "overrides": deepcopy(st.session_state.get("overrides", {})),
        "countries": list(st.session_state.get("countries") or []),
    }
    return True


def delete(name: str) -> None:
    slot = _slot()
    slot.pop(name, None)


def recall(name: str) -> bool:
    """Activate the named scenario: replace live overrides + countries."""
    slot = _slot()
    snap = slot.get(name)
    if snap is None:
        return False
    st.session_state["overrides"] = deepcopy(snap.get("overrides", {}))
    countries = snap.get("countries") or []
    if countries:
        st.session_state["countries"] = list(countries)
    return True


def metadata(name: str) -> Dict:
    return _slot().get(name, {})


def n_override_count(name: str) -> int:
    return len(_slot().get(name, {}).get("overrides", {}))

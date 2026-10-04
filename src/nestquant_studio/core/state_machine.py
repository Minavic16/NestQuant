"""Hypothesis status transitions — deterministic, approval-aware."""
from __future__ import annotations

from dataclasses import dataclass

TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"filtered", "killed", "archived"},
    "filtered": {"ranked", "killed", "archived"},
    "ranked": {"awaiting_entry_approval", "killed", "archived"},
    "awaiting_entry_approval": {"active", "killed", "archived"},
    "active": {"search_defined", "killed", "archived"},
    "search_defined": {"generating", "killed", "archived"},
    "generating": {"low_cost_filter", "killed", "archived"},
    "low_cost_filter": {"in_ladder", "killed", "archived"},
    "in_ladder": {"assessed", "killed", "archived"},
    "assessed": {"composite_proposed", "killed", "archived"},
    "composite_proposed": {"composite_approved", "assessed", "killed", "archived"},
    "composite_approved": {"archived"},
    "killed": {"archived"},
    "archived": set(),
}

NEEDS_APPROVAL = {
    ("awaiting_entry_approval", "active"),
    ("composite_proposed", "composite_approved"),
}


@dataclass
class TransitionError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def can_transition(frm: str, to: str, *, has_approval: bool = False) -> bool:
    if to not in TRANSITIONS.get(frm, set()):
        return False
    if (frm, to) in NEEDS_APPROVAL and not has_approval:
        return False
    return True


def assert_transition(frm: str, to: str, *, has_approval: bool = False) -> None:
    if to not in TRANSITIONS.get(frm, set()):
        raise TransitionError(f"illegal transition {frm} -> {to}")
    if (frm, to) in NEEDS_APPROVAL and not has_approval:
        raise TransitionError(f"transition {frm} -> {to} requires approval")
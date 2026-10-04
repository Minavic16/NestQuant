from nestquant_studio.core.state_machine import (
    TransitionError,
    assert_transition,
    can_transition,
)


def test_approval_gate():
    assert can_transition("ranked", "awaiting_entry_approval")
    assert not can_transition("awaiting_entry_approval", "active", has_approval=False)
    assert can_transition("awaiting_entry_approval", "active", has_approval=True)


def test_illegal():
    try:
        assert_transition("discovered", "in_ladder")
        assert False
    except TransitionError:
        pass
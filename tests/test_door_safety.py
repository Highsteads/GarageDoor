#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_door_safety.py
# Description: The garage door is a security device, so these pin down what
#              must never happen: a press after a restart, a second press that
#              reverses a door already doing what was asked, a press the
#              repeat-press guard fails to catch, and an alarm silenced by a
#              tick that raised.
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.1
#
# Uses the stubbed-Indigo `plugin` fixture from test_plugin_smoke.py (shared
# through conftest.py): door 1, bottom contact 101, top contact 102, relay 103.
# Tests marked xfail describe a real fault found in review that is not fixed
# yet; each reason names the fault so the fix can turn them green.
#
# v1.1 (01-11-2026): the Open-while-opening and Close-while-closing faults
# are fixed in plugin 1.12, so those two are ordinary tests now; added tests
# for the HomeKit mirror and the did-the-door-move check.

import types
import time

import pytest


def _act(door, **props):
    return types.SimpleNamespace(deviceId=door.id, props=props)


def _trigger(tid, event_id, door_id=""):
    return types.SimpleNamespace(id=tid, name=f"t{tid}", pluginTypeId=event_id,
                                 pluginProps={"doorDeviceId": door_id})


def _relay_presses(ind):
    return [c for c in ind.commands if c == ("on", 103)]


def _set_contacts(ind, bottom, top):
    ind.devices[101].states["contact"] = bottom
    ind.devices[102].states["contact"] = top


def _control_on(p):
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()


# ── restart ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bottom,top", [(False, True),     # open
                                        (False, False),    # part-way
                                        (None, None),      # silent sensors
                                        (True, True)])     # contradiction
def test_a_restart_never_presses_the_button(plugin, bottom, top):
    """Whatever the door looks like when the plugin starts, starting must not
    operate it — with Shadow Mode OFF, the dangerous case."""
    p, ind, door, _ = plugin
    _control_on(p)
    _set_contacts(ind, bottom, top)
    p.deviceStartComm(door)
    for _ in range(3):
        p._evaluate(door.id)
    assert _relay_presses(ind) == []


def test_a_restart_with_the_door_open_fires_no_door_events(plugin):
    """Triggers on Door Opened must not re-run just because the plugin restarted."""
    p, ind, door, _ = plugin
    _control_on(p)
    for i, ev in enumerate(("doorOpened", "doorClosed", "doorStartedMoving",
                            "doorStartedOpening", "sensorFault"), start=1):
        p.triggerStartProcessing(_trigger(i, ev))
    _set_contacts(ind, False, True)
    p.deviceStartComm(door)
    assert [c for c in ind.commands if c[0] == "trigger"] == []


# ── one press per request ──────────────────────────────────────────────

def test_open_while_already_opening_does_not_press_again(plugin):
    p, ind, door, _ = plugin
    _control_on(p)
    p.deviceStartComm(door)                     # closed
    p.actionOpenDoor(_act(door))
    assert len(_relay_presses(ind)) == 1
    _set_contacts(ind, False, False)            # door now travelling up
    p._evaluate(door.id)
    assert door.states["doorState"] == "opening"
    p.doors[door.id]["last_pulse_at"] -= 10     # 10 s later: past the window
    p.actionOpenDoor(_act(door))
    assert len(_relay_presses(ind)) == 1


def test_close_while_already_closing_does_not_press_again(plugin):
    p, ind, door, _ = plugin
    _control_on(p)
    _set_contacts(ind, False, True)
    p.deviceStartComm(door)                     # open
    p.actionCloseDoor(_act(door))
    _set_contacts(ind, False, False)            # travelling down
    p._evaluate(door.id)
    assert door.states["doorState"] == "closing"
    p.doors[door.id]["last_pulse_at"] -= 10
    p.actionCloseDoor(_act(door))
    assert len(_relay_presses(ind)) == 1


def test_open_on_a_closed_door_presses_exactly_once(plugin):
    p, ind, door, _ = plugin
    _control_on(p)
    p.deviceStartComm(door)
    p.actionOpenDoor(_act(door))
    assert len(_relay_presses(ind)) == 1
    assert ("off", 103) in ind.commands          # and it let go


def test_shadow_mode_blocks_every_kind_of_press(plugin):
    p, ind, door, _ = plugin
    p.startup()                                  # fixture default: shadow on
    p.deviceStartComm(door)
    for fn in (p.actionOpenDoor, p.actionCloseDoor, p.actionToggleDoor, p.actionPulseRelay):
        p.doors[door.id]["last_pulse_at"] = 0.0
        fn(_act(door))
    assert _relay_presses(ind) == []


@pytest.mark.xfail(strict=True, reason=(
    "BUG: in _pulse, if turnOn succeeds but turnOff raises, the press DID "
    "happen but last_pulse_at is never recorded, so the repeat-press guard "
    "lets an immediate retry press again and reverse the door."))
def test_a_press_whose_release_failed_still_counts_for_the_repeat_guard(plugin):
    p, ind, door, _ = plugin
    _control_on(p)
    p.deviceStartComm(door)
    real_off = ind.device.turnOff
    calls = {"n": 0}

    def flaky_off(i):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("Z-Wave timeout")
        real_off(i)

    ind.device.turnOff = flaky_off
    p.actionToggleDoor(_act(door))
    p.actionToggleDoor(_act(door))               # a second later
    assert len(_relay_presses(ind)) == 1


# ── the alarm keeps running ────────────────────────────────────────────

def test_the_tick_loop_survives_a_door_that_raises(plugin, monkeypatch):
    """One bad tick must not kill the thread that runs the alarm."""
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    ticks = {"n": 0}

    def boom(_dev_id, initial=False):
        ticks["n"] += 1
        raise RuntimeError("bad door")

    def sleep(_s):
        if ticks["n"] >= 3:
            raise p.StopThread()

    monkeypatch.setattr(p, "_evaluate", boom)
    monkeypatch.setattr(p, "sleep", sleep)
    p.runConcurrentThread()                      # returns only via StopThread
    assert ticks["n"] == 3


def test_an_unknown_door_still_alarms_when_left(plugin):
    """Unknown is not reassurance: a door whose sensors went quiet while it
    was open must still raise the left-open alarm."""
    p, ind, door, _ = plugin
    p.startup()
    p.triggerStartProcessing(_trigger(1, "doorLeftOpen"))
    p.triggerStartProcessing(_trigger(2, "doorStillOpen"))
    _set_contacts(ind, False, True)
    p.deviceStartComm(door)
    ind.devices[102].errorState = "offline"      # top sensor lost
    p._evaluate(door.id)
    assert door.states["doorState"] == "unknown"
    p.doors[door.id]["left_closed_at"] = time.time() - 16 * 60
    p._evaluate(door.id)
    fired = [c[1] for c in ind.commands if c[0] == "trigger"]
    assert "doorLeftOpen" in fired or "doorStillOpen" in fired


def test_an_event_scoped_to_another_door_does_not_fire(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.triggerStartProcessing(_trigger(1, "doorOpened", door_id="999"))
    p.triggerStartProcessing(_trigger(2, "doorOpened", door_id=str(door.id)))
    p.triggerStartProcessing(_trigger(3, "doorOpened", door_id=""))
    p.deviceStartComm(door)
    _set_contacts(ind, False, True)
    p._evaluate(door.id)
    fired = [c for c in ind.commands if c[0] == "trigger"]
    assert len(fired) == 2


def test_a_sensor_fault_event_fires_once_not_every_tick(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.triggerStartProcessing(_trigger(1, "sensorFault"))
    p.deviceStartComm(door)
    ind.devices[101].errorState = "offline"
    for _ in range(5):
        p._evaluate(door.id)
    assert [c for c in ind.commands if c == ("trigger", "sensorFault")] == \
        [("trigger", "sensorFault")]


# ── v1.12: no second press for a door already heading that way ────────

def test_open_while_closing_still_presses(plugin):
    """Only the SAME direction is refused. Asked to open a closing door, the
    plugin still presses, as it always has."""
    p, ind, door, _ = plugin
    _control_on(p)
    _set_contacts(ind, False, True)
    p.deviceStartComm(door)                     # open
    _set_contacts(ind, False, False)            # travelling down
    p._evaluate(door.id)
    assert door.states["doorState"] == "closing"
    p.actionOpenDoor(_act(door))
    assert len(_relay_presses(ind)) == 1


@pytest.mark.parametrize("action", ["actionOpenDoor", "actionCloseDoor"])
def test_a_door_moving_with_no_known_direction_is_not_pressed(plugin, action):
    """Started mid-travel: the plugin has not seen which end it left, so a
    press could do either. Toggle is the deliberate way round this."""
    p, ind, door, _ = plugin
    _control_on(p)
    _set_contacts(ind, False, False)
    p.deviceStartComm(door)
    assert door.states["doorState"] == "moving"
    getattr(p, action)(_act(door))
    assert _relay_presses(ind) == []
    p.actionToggleDoor(_act(door))
    assert len(_relay_presses(ind)) == 1


# ── v1.12: HomeKit is never left on a stale "closed" ───────────────────

def _var_writes(ind):
    return [c[2] for c in ind.commands if c[0] == "var"]


def test_homekit_says_open_when_a_closed_doors_sensor_drops(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)                     # closed
    assert _var_writes(ind)[-1] == "on"         # inverted: on = closed
    ind.devices[101].errorState = "offline"
    p._evaluate(door.id)
    assert door.states["doorState"] == "unknown"
    assert _var_writes(ind)[-1] == "off"        # shown as open, not stale closed


def test_homekit_is_not_rewritten_every_tick(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    for _ in range(5):
        p._evaluate(door.id)
    assert len(_var_writes(ind)) == 1


def test_a_failed_homekit_write_is_tried_again(plugin):
    p, ind, door, _ = plugin
    p.startup()
    real = ind.variable.updateValue
    calls = {"n": 0}

    def flaky(vid, val):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("variable busy")
        real(vid, val)

    ind.variable.updateValue = flaky
    p.deviceStartComm(door)                     # first write raises
    assert _var_writes(ind) == []
    p._evaluate(door.id)                        # inside the retry wait: nothing
    assert _var_writes(ind) == []
    p.doors[door.id]["hk_fail_at"] -= 61        # a minute later
    p._evaluate(door.id)
    assert _var_writes(ind) == ["on"]


# ── v1.12: a press that does not move the door is noticed ──────────────

def test_a_press_that_does_not_move_the_door_is_reported_once(plugin):
    p, ind, door, _ = plugin
    _control_on(p)
    p.triggerStartProcessing(_trigger(1, "doorDidNotMove"))
    p.deviceStartComm(door)                     # closed
    p.actionOpenDoor(_act(door))
    p._evaluate(door.id)
    assert ("trigger", "doorDidNotMove") not in ind.commands   # too soon
    p.doors[door.id]["press_check"]["at"] -= 16
    for _ in range(3):
        p._evaluate(door.id)
    assert ind.commands.count(("trigger", "doorDidNotMove")) == 1


def test_a_press_that_moves_the_door_is_not_reported(plugin):
    p, ind, door, _ = plugin
    _control_on(p)
    p.triggerStartProcessing(_trigger(1, "doorDidNotMove"))
    p.deviceStartComm(door)
    p.actionOpenDoor(_act(door))
    _set_contacts(ind, False, False)            # it left the bottom
    p._evaluate(door.id)
    assert p.doors[door.id]["press_check"] is None
    _set_contacts(ind, True, False)             # even if it later comes back
    p._evaluate(door.id)
    assert ("trigger", "doorDidNotMove") not in ind.commands


def test_shadow_mode_makes_no_press_to_check(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    p.actionOpenDoor(_act(door))
    assert p.doors[door.id]["press_check"] is None

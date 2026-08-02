#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_garage_logic.py
# Description: Contract tests for the garage door's decisions — state, alarm,
#              light, and the HomeKit mirror.
# Author:      CliveS & Claude Opus 5
# Date:        02-08-2026
# Version:     1.0
#
# Run: python3 -m pytest tests -q     (or tests/run.sh for the full gate)

import os
import sys

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "GarageDoor.indigoPlugin", "Contents", "Server Plugin"))

import garage_logic as g  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# Reading the two position sensors
# ══════════════════════════════════════════════════════════════════════

def test_closed_is_bottom_reed_made_only():
    assert g.derive_state(True, False) == (g.CLOSED, True)


def test_open_is_top_reed_made_only():
    assert g.derive_state(False, True) == (g.OPEN, True)


def test_both_reeds_apart_is_moving():
    assert g.derive_state(False, False) == (g.MOVING, True)


def test_moving_past_the_travel_timeout_is_stuck():
    assert g.derive_state(False, False, moving_seconds=31) == (g.STUCK, True)
    # And not a moment before — the boundary is where a real door lives.
    assert g.derive_state(False, False, moving_seconds=30) == (g.MOVING, True)


def test_both_reeds_made_is_a_sensor_fault():
    """A door cannot be at the bottom and the top at once."""
    state, healthy = g.derive_state(True, True)
    assert state == g.UNKNOWN
    assert healthy is False


@pytest.mark.parametrize("bottom, top", [
    (None, True), (True, None), (None, None),
    ("", True), ("n/a", False),
])
def test_a_silent_sensor_never_yields_a_position(bottom, top):
    """THE trap. `None == False` is True in Python, so a sensor that has never
    reported would otherwise satisfy a test for 'reed apart' and the door would
    be declared open or closed on one working sensor and one dead one."""
    state, healthy = g.derive_state(bottom, top)
    assert state == g.UNKNOWN
    assert healthy is True          # silent, not faulty — a different problem


def test_string_booleans_from_the_v2_api_are_understood():
    """Custom states can arrive as the strings "True"/"False"."""
    assert g.derive_state("true", "false") == (g.CLOSED, True)
    assert g.derive_state("False", "True") == (g.OPEN, True)
    assert g.derive_state(0, 1) == (g.OPEN, True)


def test_unknown_is_not_reassurance():
    assert g.is_shut(g.CLOSED) is True
    for s in (g.OPEN, g.MOVING, g.STUCK, g.UNKNOWN):
        assert g.is_shut(s) is False


# ══════════════════════════════════════════════════════════════════════
# The alarm
# ══════════════════════════════════════════════════════════════════════

def test_a_closed_door_never_alarms():
    level, notify = g.alarm_decision(g.CLOSED, 999, away=True, night=True)
    assert (level, notify) == (g.ALERT_NONE, False)


def test_quiet_until_the_first_threshold():
    level, notify = g.alarm_decision(g.OPEN, 14, away=False, night=False)
    assert (level, notify) == (g.ALERT_NONE, False)


def test_first_alert_at_fifteen_minutes():
    level, notify = g.alarm_decision(g.OPEN, 15, away=False, night=False)
    assert level == g.ALERT_OPEN
    assert notify is True


def test_an_empty_house_is_urgent_immediately():
    """Not an oversight — a different event, and it should not wait 15 minutes."""
    level, notify = g.alarm_decision(g.OPEN, 0, away=True, night=False)
    assert level == g.ALERT_URGENT
    assert notify is True


def test_stuck_part_way_is_urgent_immediately():
    level, notify = g.alarm_decision(g.STUCK, 0, away=False, night=False)
    assert level == g.ALERT_URGENT
    assert notify is True


def test_dark_escalates_at_the_first_threshold_not_before():
    assert g.alarm_decision(g.OPEN, 14, False, True)[0] == g.ALERT_NONE
    assert g.alarm_decision(g.OPEN, 15, False, True)[0] == g.ALERT_URGENT


def test_long_enough_is_urgent_on_its_own():
    assert g.alarm_decision(g.OPEN, 44, False, False)[0] == g.ALERT_OPEN
    assert g.alarm_decision(g.OPEN, 45, False, False)[0] == g.ALERT_URGENT


def test_it_does_not_nag_every_tick():
    """Having said it at 15 minutes, it stays quiet until the repeat interval."""
    _, notify = g.alarm_decision(g.OPEN, 16, False, False,
                                 last_level=g.ALERT_OPEN, last_notified_minutes=15)
    assert notify is False
    _, notify = g.alarm_decision(g.OPEN, 30, False, False,
                                 last_level=g.ALERT_OPEN, last_notified_minutes=15)
    assert notify is True


def test_getting_worse_always_speaks_up():
    """Escalation must not be swallowed by the repeat interval."""
    level, notify = g.alarm_decision(g.OPEN, 46, False, False,
                                     last_level=g.ALERT_OPEN, last_notified_minutes=45)
    assert level == g.ALERT_URGENT
    assert notify is True


def test_a_door_that_is_merely_moving_still_counts_as_not_shut():
    """Fifteen minutes of 'moving' is a real problem, whatever the label."""
    assert g.alarm_decision(g.MOVING, 15, False, False)[0] == g.ALERT_OPEN


# ══════════════════════════════════════════════════════════════════════
# Config handling — every install starts blank
# ══════════════════════════════════════════════════════════════════════

def test_blank_config_falls_back_to_the_shipped_defaults():
    for cfg in ({}, None, {"firstAlertMinutes": ""}, {"firstAlertMinutes": None}):
        assert g.cfg_get(cfg, "firstAlertMinutes") == 15


def test_junk_in_a_numeric_field_does_not_raise():
    assert g.cfg_get({"firstAlertMinutes": "abc"}, "firstAlertMinutes") == 15
    assert g.cfg_get({"travelTimeoutSeconds": "  "}, "travelTimeoutSeconds") == 30


def test_numbers_stored_as_strings_are_honoured():
    """Indigo re-serialises a saved dialog value as a string."""
    assert g.cfg_get({"firstAlertMinutes": "5"}, "firstAlertMinutes") == 5
    assert g.alarm_decision(g.OPEN, 5, False, False,
                            cfg={"firstAlertMinutes": "5"})[0] == g.ALERT_OPEN


def test_the_string_false_is_false_not_true():
    assert g.as_bool("false") is False
    assert g.as_bool("False") is False
    assert g.as_bool("true") is True


def test_an_unrecognised_string_returns_the_default():
    """Unknown is not False — that silently flipped default-on settings off."""
    assert g.as_bool("wibble", default=True) is True
    assert g.as_bool("wibble", default=False) is False


def test_away_urgency_can_be_turned_off():
    cfg = {"urgentWhenAway": False}
    assert g.alarm_decision(g.OPEN, 0, away=True, night=False, cfg=cfg)[0] == g.ALERT_NONE


# ══════════════════════════════════════════════════════════════════════
# The garage light
# ══════════════════════════════════════════════════════════════════════

def test_light_comes_on_when_someone_is_there_and_it_is_dark():
    assert g.light_decision(g.OPEN, present=True, lux=5) is True


def test_light_stays_off_in_daylight():
    assert g.light_decision(g.OPEN, present=True, lux=500) is False


def test_light_stays_off_when_nobody_walked_in():
    """The neighbour's remote, or a scheduled close, does not need the light."""
    assert g.light_decision(g.OPEN, present=False, lux=5) is False


def test_light_goes_off_when_the_door_shuts():
    assert g.light_decision(g.CLOSED, present=True, lux=5) is False


def test_no_opinion_without_a_reading():
    """Missing sensors mean leave the light alone, not guess at it."""
    assert g.light_decision(g.OPEN, present=None, lux=5) is None
    assert g.light_decision(g.OPEN, present=True, lux=None) is None
    assert g.light_decision(g.OPEN, present=True, lux="dim") is None


def test_gates_can_be_turned_off_individually():
    cfg = {"lightOnlyIfPresent": False, "lightOnlyIfDark": False}
    assert g.light_decision(g.OPEN, present=None, lux=None, cfg=cfg) is True


# ══════════════════════════════════════════════════════════════════════
# The HomeKit mirror
# ══════════════════════════════════════════════════════════════════════

def test_homekit_variable_is_inverted():
    """HomeKitLink maps ON to Closed, so "on" means shut. Easy to get backwards."""
    assert g.homekit_value(g.CLOSED) == "on"
    assert g.homekit_value(g.OPEN) == "off"


def test_homekit_inversion_is_optional():
    assert g.homekit_value(g.CLOSED, invert=False) == "off"
    assert g.homekit_value(g.OPEN, invert=False) == "on"


@pytest.mark.parametrize("state", [g.MOVING, g.STUCK, g.UNKNOWN])
def test_an_uncertain_door_publishes_nothing(state):
    """Never tell HomeKit the garage is shut when we do not know that."""
    assert g.homekit_value(state) is None


# ══════════════════════════════════════════════════════════════════════
# Wording
# ══════════════════════════════════════════════════════════════════════

def test_the_message_says_what_is_wrong():
    assert g.describe(g.CLOSED) == "Garage door is closed"
    assert "stuck part-way" in g.describe(g.STUCK)
    assert "for 20 minutes" in g.describe(g.OPEN, open_minutes=20)
    msg = g.describe(g.OPEN, open_minutes=20, away=True, night=True)
    assert "Nobody is home." in msg and "It is dark." in msg


def test_a_freshly_opened_door_does_not_claim_zero_minutes():
    assert "minutes" not in g.describe(g.OPEN, open_minutes=0)

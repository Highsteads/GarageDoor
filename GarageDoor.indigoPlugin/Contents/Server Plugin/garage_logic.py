#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    garage_logic.py
# Description: Every decision this plugin makes, as pure functions with no
#              Indigo import — the door's state, when to raise the alarm, when
#              to light the garage, and what to publish for HomeKit.
# Author:      CliveS & Claude Opus 5
# Date:        02-08-2026
# Version:     1.0
#
# WHY THIS FILE EXISTS SEPARATELY
# The plugin around it is plumbing: read a device, write a state, fire an event.
# Everything that could be WRONG lives here, and none of it needs Indigo, a
# radio or a door. tests/test_garage_logic.py drives these functions directly,
# so the tests exercise what actually ships rather than a copy of it.

# ── door states ──────────────────────────────────────────────────────────
CLOSED  = "closed"
OPEN    = "open"
MOVING  = "moving"
STUCK   = "stuck"
UNKNOWN = "unknown"

# ── alert levels ─────────────────────────────────────────────────────────
ALERT_NONE   = 0
ALERT_OPEN   = 1     # left open past the first threshold
ALERT_URGENT = 2     # empty house, stuck, dark, or open a long time

DEFAULTS = {
    "travelTimeoutSeconds":  30,
    "firstAlertMinutes":     15,
    "escalateAfterMinutes":  45,
    "repeatEveryMinutes":    15,
    "urgentWhenAway":        True,
    "urgentWhenDark":        True,
    "lightOnlyIfDark":       True,
    "lightOnlyIfPresent":    False,
    "luxThreshold":          30,
    "lampsFollowDoor":       True,
}


def cfg_get(cfg, key):
    """Read a tunable, falling back to the shipped default.

    A blank config field must never become 0 or an exception — every install
    starts with nothing filled in, and the alarm has to work anyway.
    """
    cfg = cfg or {}
    raw = cfg.get(key, None)
    default = DEFAULTS.get(key)
    if raw is None or raw == "":
        return default
    if isinstance(default, bool):
        return as_bool(raw, default)
    try:
        return type(default)(raw)
    except (TypeError, ValueError):
        return default


def as_bool(value, default=False):
    """Coerce a value that may be a real bool, a number, or a string.

    Indigo re-serialises saved dialog values as strings, and bool("false") is
    True — which is exactly the wrong answer. An unrecognised string is unknown,
    so it returns the DEFAULT rather than silently False.
    """
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    return default


def as_reed(value):
    """Read one contact sensor. True = reed made, False = apart, None = UNKNOWN.

    THE TRAP THIS EXISTS FOR: an absent state reads back as None, and in Python
    `None == False` is True. A sensor that has never reported once would
    therefore satisfy a test for "reed apart" and the door would be declared
    open or closed on the word of one working sensor and one silent one.
    Absent is never an answer here, in either direction.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    return None            # a string we do not recognise is not a reading


def derive_state(bottom_contact, top_contact, moving_seconds=0.0, cfg=None):
    """Work out where the door is from its two position sensors.

    Mirrors Garage_Door_Controller.py's get_door_state(). Both sensors report
    whether the door is at THAT END of its travel, so `contact` means the reed
    is made. Note this is the exact inverse of the devices' own `onState`, which
    is why nothing here touches onState.

    Returns (state, sensors_healthy).
    """
    bottom = as_reed(bottom_contact)
    top    = as_reed(top_contact)

    if bottom is None or top is None:
        return UNKNOWN, True          # silent sensor, not a faulty one

    if bottom and top:
        # The door cannot be at the bottom and the top at once. One sensor is
        # lying, or a magnet has come adrift.
        return UNKNOWN, False

    if bottom and not top:
        return CLOSED, True
    if top and not bottom:
        return OPEN, True

    # Neither reed made: the door is between the two ends. That is normal for
    # about twenty seconds and a problem after that.
    timeout = cfg_get(cfg, "travelTimeoutSeconds")
    if moving_seconds > timeout:
        return STUCK, True
    return MOVING, True


def is_shut(state):
    """Only CLOSED counts as shut. Unknown is not reassurance."""
    return state == CLOSED


def alarm_decision(state, open_minutes, away, night, cfg=None,
                   last_level=ALERT_NONE, last_notified_minutes=None):
    """Decide the alert level, and whether to say something about it now.

    Urgency is not a flat fifteen minutes. A door open in daylight with somebody
    home is an oversight. The same door with the house empty is a different
    event and should not wait.

    Returns (level, notify).
    """
    if is_shut(state):
        return ALERT_NONE, False

    first    = cfg_get(cfg, "firstAlertMinutes")
    escalate = cfg_get(cfg, "escalateAfterMinutes")
    repeat   = cfg_get(cfg, "repeatEveryMinutes")

    if state == STUCK:
        level = ALERT_URGENT                       # jammed part-way, tell me now
    elif away and cfg_get(cfg, "urgentWhenAway"):
        level = ALERT_URGENT                       # empty house: a security event
    elif open_minutes >= escalate:
        level = ALERT_URGENT
    elif open_minutes >= first:
        level = ALERT_URGENT if (night and cfg_get(cfg, "urgentWhenDark")) else ALERT_OPEN
    else:
        level = ALERT_NONE

    if level == ALERT_NONE:
        return level, False

    # Say it once, then only when it gets worse or the repeat interval passes.
    if level > last_level:
        return level, True
    if last_notified_minutes is None:
        return level, True
    if repeat > 0 and (open_minutes - last_notified_minutes) >= repeat:
        return level, True
    return level, False


def light_decision(state, present, lux, cfg=None):
    """Should the garage light be on?

    On when the door is not shut and it is dark enough to want it, off the
    moment the door closes. Presence-gating is available but OFF by default:
    a light that waits until it is certain somebody is in the garage leaves
    you standing in the dark, which is not what a garage light is for.

    Returns True (on), False (off), or None (no opinion — leave it alone).
    """
    if is_shut(state):
        return False

    if cfg_get(cfg, "lightOnlyIfPresent"):
        p = as_reed(present)
        if p is None:
            return None                # no presence reading: do not guess
        if not p:
            return False

    if cfg_get(cfg, "lightOnlyIfDark"):
        if lux is None or lux == "":
            return None                # no lux reading: do not guess
        try:
            if float(lux) > cfg_get(cfg, "luxThreshold"):
                return False
        except (TypeError, ValueError):
            return None

    return True


# ── lamp signalling ──────────────────────────────────────────────────────
# The house lamps that announce the door: blue while it moves, red while it is
# open, and on closing they go back to matching a reference lamp elsewhere in
# the house. Ported from Garage_Door_Controller.py so the scripts can retire.
#
# Every part is optional. A plugin that carries one house's decoration is no
# use to anyone else, so nothing here fires unless the devices are configured,
# and "no opinion" is a first-class answer.

HALL_MOVING  = "moving"
HALL_OPEN    = "open"
HALL_RESTORE = "restore"
HALL_OFF     = "off"


def lamp_plan(state, restore_reference_on=None, cfg=None):
    """What the lamps should do for a given door state.

    Returns {"hall": <HALL_* or None>, "conservatory": True/False/None}, where
    None means leave it alone. Pure — the plugin turns this into commands.
    """
    if not cfg_get(cfg, "lampsFollowDoor"):
        return {"hall": None, "conservatory": None}

    if state in (MOVING, UNKNOWN):
        # Moving is a transient. Say so on the hall lamp and touch nothing else,
        # or the conservatory flickers on every pass of the door.
        return {"hall": HALL_MOVING, "conservatory": None}

    if state == OPEN:
        return {"hall": HALL_OPEN, "conservatory": True}

    if state == CLOSED:
        # Closing restores the house to whatever the reference lamp says. With
        # no reference configured, "off" is the sane reading of a shut door.
        if restore_reference_on:
            return {"hall": HALL_RESTORE, "conservatory": True}
        return {"hall": HALL_OFF, "conservatory": False}

    if state == STUCK:
        # Leave the signal showing. A stuck door should not look tidy.
        return {"hall": HALL_MOVING, "conservatory": None}

    return {"hall": None, "conservatory": None}


def parse_rgb(text, default=(100, 100, 100)):
    """Read an "R,G,B" config field into three 0-100 ints.

    Config fields are free text, so this has to survive anything: blanks,
    spaces, too few values, junk, and numbers outside the range.
    """
    if text is None:
        return default
    parts = [p.strip() for p in str(text).replace(";", ",").split(",")]
    parts = [p for p in parts if p != ""]
    if len(parts) < 3:
        return default
    out = []
    for p in parts[:3]:
        try:
            out.append(max(0, min(100, int(float(p)))))
        except (TypeError, ValueError):
            return default
    return tuple(out)


def homekit_value(state, invert=True):
    """What to write to the HomeKit mirror variable.

    HomeKitLink-Siri maps ON to Closed here, so the variable runs inverted
    against every instinct: "on" means the garage is SHUT. Only a definite
    reading is published — an unknown door must not be reported as closed.
    """
    if state == CLOSED:
        return "on" if invert else "off"
    if state == OPEN:
        return "off" if invert else "on"
    return None


def describe(state, open_minutes=None, away=False, night=False):
    """One line of plain English for a log or a notification."""
    if state == CLOSED:
        return "Garage door is closed"

    if state == STUCK:
        head = "Garage door is stuck part-way"
    elif state == MOVING:
        head = "Garage door is moving"
    elif state == UNKNOWN:
        head = "Garage door position is unknown"
    else:
        head = "Garage door is open"

    if open_minutes is not None and open_minutes >= 1:
        head += f" (for {int(open_minutes)} minutes)"

    extra = []
    if away:
        extra.append("Nobody is home.")
    if night:
        extra.append("It is dark.")
    return head + ("  " + " ".join(extra) if extra else "")

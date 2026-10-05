#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    plugin.py
# Description: One Indigo device that owns the garage door — its real position,
#              how long it has been open, the alarm when it is left that way,
#              and the light that follows whoever walked in.
# Author:      CliveS & Claude Fable 5.1, Claude Opus 5.5, Claude Sonnet 5.5
# Date:        05-10-2026
# Version:     1.11.1
#
# v1.11.1 (05-10-2026, Claude Sonnet 5.5): saving the settings names the mode
# you just chose, not the one you left, and turning Shadow Mode off sets the
# hall and conservatory lamps for the door's present state straight away,
# leaving any lamp that is already right alone.
#
# v1.11 (05-10-2026, Claude Opus 5.5): a contact sensor that is disabled, in
# error or reported offline is no reading, so the door reads Unknown with
# Sensors healthy false and a Sensor problem naming the sensor, instead of
# "closed" on the stale value Zigbee2MQTTBridge leaves behind; Open and Close
# refuse to guess while the position is unknown. A restart keeps the time the
# door was opened and does not repeat an alert already sent. The garage light
# is only marked done once the command has gone, so a failed command is tried
# again and turning Shadow Mode off brings the light into line.
#
# v1.10 (03-10-2026, Claude Sonnet 5.5): the Door state itself now reads
# opening or closing while the door travels (moving only when the direction is
# unknown), and two new events fire, so every trigger, script and page learns
# the direction from the one state. The Direction of travel state stays.
#
# v1.9 (03-10-2026, Claude Sonnet 5.5): a Direction of travel state (opening,
# closing or none), worked out from the end the door was last seen at, so a
# page opened while the door is moving can say which way instead of guessing.
#
# v1.8 (27-09-2026, Claude Opus 5.5): Pulse length, the repeat-press window and
# Logging level are now read; a decimal lux threshold is honoured; the Pulse
# Relay and Re-read notes are used; with no light-level sensor the light is
# judged by the Dark variable instead of never coming on; and Test Garage Door
# Setup checks the signal lamp, the second lamp and the restore reference.
#
# WHY THIS PLUGIN EXISTS
# Six separate places used to work out "is the garage open" from the two raw
# contact sensors, and they did not agree on how: some read `states.contact`,
# one read `onState`, and those two are exact inverses. Both were right, which
# is worse than one being wrong — a single tidy-up edit would have broken half
# of them silently. One device with one answer ends that.
#
# It also fixes something scripts structurally cannot do. Nothing was
# long-running, so nothing could notice time passing, which is why a
# fifteen-minute open alarm sat dead from May to August: a script runs when
# something fires it, and a timer expiring needs a listener. runConcurrentThread
# is that listener, and it needs no timer device and no trigger.
#
# SHADOW MODE
# v1.0 ships read-only. It watches, reports and alarms, but never touches the
# relay — the old scripts keep operating the door until the state machine has
# proven itself against the real thing. See the README before turning it off.

try:
    import indigo
except ImportError:
    pass

import os as _os
import sys as _sys
import time
from datetime import datetime

_sys.path.insert(0, _os.getcwd())   # bundled alongside this file
try:
    from plugin_utils import log_startup_banner
except ImportError:
    log_startup_banner = None

import garage_logic as G


PLUGIN_ID = "com.clives.indigoplugin.garagedoor"

TICK_SECONDS = 1.0          # fine enough to time travel, cheap enough to ignore
LIGHT_RETRY_SECONDS = 60    # how soon a light command that raised is tried again

# Events declared in Events.xml
EV_OPENED       = "doorOpened"
EV_CLOSED       = "doorClosed"
EV_MOVING       = "doorStartedMoving"
EV_OPENING      = "doorStartedOpening"
EV_CLOSING      = "doorStartedClosing"
EV_LEFT_OPEN    = "doorLeftOpen"
EV_STILL_OPEN   = "doorStillOpen"
EV_STUCK        = "doorStuck"
EV_SENSOR_FAULT = "sensorFault"

# Fallbacks matching the retired controller's HALL_COLORS, used when a
# colour field is blank or unreadable.
_LAMP_FALLBACK = {"moving": (0, 0, 100), "open": (100, 0, 0),
                  "restore": (100, 100, 100)}


class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        try:
            from plugin_utils import install_timestamp_filter
            install_timestamp_filter(self)
        except Exception:
            pass

        # Runtime state, keyed by device id. The single owner of everything the
        # door "is" — never duplicated into a second store.
        self.doors = {}
        self.event_triggers = {}
        self._watched = {}          # contact device id -> set of door device ids
        # Config warnings already given, for a door with no runtime state yet.
        # Per-door warnings live on the door's own entry in self.doors.
        self._warned_no_state = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def startup(self):
        self._apply_log_level(self.pluginPrefs.get("logLevel"))
        indigo.devices.subscribeToChanges()
        if self._shadow_mode():
            self.logger.info("Started in SHADOW MODE — watching and reporting, "
                             "but not operating the door")
        else:
            self.logger.info("Started with door control ENABLED")

    def shutdown(self):
        self.logger.info(f"{self.pluginDisplayName} stopped")

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        """Apply prefs live rather than making the user restart."""
        if userCancelled:
            return
        self._apply_log_level(valuesDict.get("logLevel"))
        # Indigo may not have copied the saved values into pluginPrefs yet, so
        # the new mode comes from the dialog's own values. Until 1.11.1 this
        # read pluginPrefs and could name the mode that had just been left. A
        # blank or missing field keeps the current mode.
        shadow = G.as_bool(valuesDict.get("shadowMode"), self._shadow_mode())
        mode = "SHADOW MODE (not operating the door)" if shadow \
            else "door control ENABLED"
        self.logger.info(f"Configuration saved — now in {mode}")

    def _shadow_mode(self):
        return G.as_bool(self.pluginPrefs.get("shadowMode"), True)

    def _apply_log_level(self, value):
        """Apply the Logging level pref to the EVENT LOG handler only.

        Not to self.logger: that gates before both handlers, and would throw
        Debug lines away before this plugin's own log file ever saw them.
        Until v1.8 the pref was stored and never read.
        """
        handler = getattr(self, "indigo_log_handler", None)
        if handler is None:
            return
        try:
            handler.setLevel(G.log_level(value))
        except Exception as e:
            self.logger.debug(f"Could not set the logging level: {e}")

    # ------------------------------------------------------------------
    # Device lifecycle
    # ------------------------------------------------------------------

    def deviceStartComm(self, dev):
        # A state added in a later version is hidden from a device made before
        # it until Indigo is told the state list changed (Direction of travel,
        # 1.9). Without this the first writes to it are dropped.
        try:
            dev.stateListOrDisplayStateIdChanged()
        except Exception as e:
            self.logger.debug(f"Could not refresh the state list: {e}")
        props = dict(dev.pluginProps)
        self.doors[dev.id] = {
            "props": props,
            "state": None,
            "left_closed_at": None,     # when it stopped being shut
            "moving_since": None,       # when it left a known position
            "last_settled": None,       # the end it was last seen at, closed or open
            "last_level": G.ALERT_NONE,
            "last_notified_min": None,
            "last_pulse_at": 0.0,
            "operated_by": "",
            "light_want": None,         # last light command that actually went
            "light_mode": None,         # shadow flag when light_want was set
            "light_fail_at": None,      # when a light command last raised
            "problem": None,            # what is wrong with the sensors, "" = nothing
            # What this door looked like before the plugin stopped, so a
            # restart with the door open does not start its clock again.
            "seed": {
                "stored":      G.parse_stamp(dev.states.get("leftClosedAt")),
                "heartbeat":   self._epoch(getattr(dev, "lastChanged", None)),
                "alert_level": dev.states.get("alertLevel"),
                "alert_sent":  G.parse_stamp(dev.states.get("lastAlertSent")),
            },
        }
        # Index the contacts so deviceUpdated is a dict lookup, not a scan.
        for key in ("bottomContactId", "topContactId"):
            try:
                cid = int(props.get(key) or 0)
            except (TypeError, ValueError):
                cid = 0
            if cid:
                self._watched.setdefault(cid, set()).add(dev.id)

        missing = [k for k in ("bottomContactId", "topContactId") if not props.get(k)]
        if missing:
            # Awaiting configuration is not a fault — INFO, not ERROR.
            self.logger.info(f"{dev.name}: not configured yet ({', '.join(missing)}) — "
                             "open its settings and pick the two contact sensors")
        self._evaluate(dev.id, initial=True)

    def deviceStopComm(self, dev):
        self.doors.pop(dev.id, None)
        for ids in self._watched.values():
            ids.discard(dev.id)

    def deviceUpdated(self, orig_dev, new_dev):
        super().deviceUpdated(orig_dev, new_dev)
        # Loop guard: without it, writing our own state re-enters here forever.
        if new_dev.pluginId == self.pluginId:
            return
        for door_id in self._watched.get(new_dev.id, ()):
            try:
                self._evaluate(door_id)
            except Exception as e:
                self.logger.error(f"Error handling a contact change: {e}")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def triggerStartProcessing(self, trigger):
        self.event_triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.event_triggers.pop(trigger.id, None)

    def _fire(self, event_id, dev):
        """Fire a custom event. One bad trigger must not stop the others."""
        fired = 0
        for trigger in list(self.event_triggers.values()):
            if trigger.pluginTypeId != event_id:
                continue
            # A trigger may be scoped to one door, or left to match any.
            want = str(trigger.pluginProps.get("doorDeviceId", "") or "")
            if want and want not in ("0", "-1", str(dev.id)):
                continue
            try:
                indigo.trigger.execute(trigger)
                fired += 1
            except Exception as e:
                self.logger.error(f"Could not fire trigger {trigger.name}: {e}")
        if fired:
            self.logger.debug(f"{event_id} -> {fired} trigger(s)")

    # ------------------------------------------------------------------
    # Reading the world
    # ------------------------------------------------------------------

    @staticmethod
    def _state_of(dev_id, *keys):
        """Read the first available state from another plugin's device.

        Reading a foreign device's states is fine. WRITING them is private to
        the owning plugin and raises — we never do it.
        """
        try:
            d = indigo.devices[int(dev_id)]
        except (KeyError, ValueError, TypeError):
            return None
        for k in keys:
            if k == "onState":
                v = getattr(d, "onState", None)
                if v is not None:
                    return v
            elif k in d.states:
                return d.states[k]
        return None

    @staticmethod
    def _epoch(value):
        """A device's datetime attribute (e.g. lastChanged) as epoch seconds."""
        try:
            return value.timestamp()
        except (AttributeError, TypeError, ValueError, OverflowError, OSError):
            return None

    @staticmethod
    def _contact(dev_id, label):
        """One position contact: (value, problem, lastChanged epoch).

        problem is None when the reading can be used, otherwise a sentence
        naming the sensor. A contact left blank in the settings is not a
        problem, just not configured yet. Only `contact` is read: it means the
        reed is made, the exact inverse of the device's own onState.
        """
        if not dev_id:
            return None, None, None
        try:
            d = indigo.devices[int(dev_id)]
        except (KeyError, ValueError, TypeError):
            return None, f"the {label} sensor (device {dev_id}) does not exist", None
        try:
            states = d.states
            why = G.contact_problem(enabled=getattr(d, "enabled", True),
                                    error_state=getattr(d, "errorState", ""),
                                    availability=states.get("availability"))
            changed = Plugin._epoch(getattr(d, "lastChanged", None))
            if why:
                return None, f"the {label} sensor '{d.name}' {why}", changed
            return states.get("contact"), None, changed
        except Exception as e:
            return None, f"the {label} sensor (device {dev_id}) cannot be read: {e}", None

    @staticmethod
    def _var_true(name_or_id):
        """Read a variable BY NAME, falling back to an id.

        A variable deleted and recreated keeps its name but not its id, so a
        pinned id breaks silently. Name first.
        """
        if not name_or_id:
            return False
        for key in (str(name_or_id), ):
            try:
                return str(indigo.variables[key].value).strip().lower() == "true"
            except (KeyError, ValueError):
                pass
        try:
            return str(indigo.variables[int(name_or_id)].value).strip().lower() == "true"
        except (KeyError, ValueError, TypeError):
            return False

    @staticmethod
    def _var_reading(name_or_id):
        """A variable as True, False or None (missing, or not true/false).

        _var_true answers False for a variable it cannot find, which is right
        for the alarm and wrong for the light: "cannot tell whether it is dark"
        must not read as "it is light".
        """
        if not name_or_id:
            return None
        for key in (str(name_or_id), ):
            try:
                return G.as_reed(indigo.variables[key].value)
            except (KeyError, ValueError):
                pass
        try:
            return G.as_reed(indigo.variables[int(name_or_id)].value)
        except (KeyError, ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # ConfigUI list callbacks
    # ------------------------------------------------------------------
    # Indigo callbacks have rigid signatures full of parameters you never use.
    # Underscore-prefix the unused ones — documents intent, silences linters.

    @staticmethod
    def getDeviceList(_filter="", _values_dict=None, _type_id="", _target_id=0):
        """Every Indigo device, so a user can pick contacts, relays and lights
        whatever plugin owns them."""
        items = []
        for d in indigo.devices:
            try:
                items.append((str(d.id), d.name))
            except Exception:
                continue
        items.sort(key=lambda x: x[1].lower())
        return [("", "- none -")] + items

    def getDoorList(self, _filter="", _values_dict=None, _type_id="", _target_id=0):
        """This plugin's own door devices, for scoping an event to one door."""
        items = [(str(d.id), d.name) for d in indigo.devices.iter("self.garageDoor")]
        items.sort(key=lambda x: x[1].lower())
        return [("", "- any door -")] + items

    # ------------------------------------------------------------------
    # The state machine
    # ------------------------------------------------------------------

    def _evaluate(self, dev_id, initial=False):
        st = self.doors.get(dev_id)
        if st is None:
            return
        try:
            dev = indigo.devices[dev_id]
        except KeyError:
            return
        props = st["props"]
        now = time.time()

        bottom, b_prob, b_changed = self._contact(props.get("bottomContactId"), "bottom contact")
        top,    t_prob, _         = self._contact(props.get("topContactId"), "top contact")

        moving_for = (now - st["moving_since"]) if st["moving_since"] else 0.0
        state, healthy, problem = G.assess_door(bottom, top, moving_for, props,
                                                bottom_problem=b_prob, top_problem=t_prob)

        previous = st["state"]
        st["state"] = state

        # Did Shadow Mode change since the lamps were last looked at? The lamps
        # are otherwise only set when the door changes state.
        shadow_now = self._shadow_mode()
        lamps_mode_changed = st.get("lamps_mode") is not None and st["lamps_mode"] != shadow_now
        st["lamps_mode"] = shadow_now

        # Which way it is travelling, from the end it was last seen at.
        direction = G.door_direction(state, st.get("last_settled"))
        if state in (G.CLOSED, G.OPEN):
            st["last_settled"] = state

        # --- transitions -------------------------------------------------
        if state != previous:
            if state in (G.MOVING, G.UNKNOWN) and st["moving_since"] is None:
                st["moving_since"] = now
            if state in (G.CLOSED, G.OPEN):
                if st["moving_since"]:
                    self._set(dev, "travelSeconds", int(now - st["moving_since"]))
                st["moving_since"] = None

            if G.is_shut(state):
                st["left_closed_at"] = None
                st["last_level"] = G.ALERT_NONE
                st["last_notified_min"] = None
            elif st["left_closed_at"] is None:
                if initial:
                    self._seed_opening(dev, st, state, now, b_changed, b_prob)
                else:
                    st["left_closed_at"] = now

            if not initial:
                if state == G.OPEN:
                    self._set(dev, "lastOpened", self._stamp())
                    self._fire(EV_OPENED, dev)
                elif state == G.CLOSED:
                    self._set(dev, "lastClosed", self._stamp())
                    self._fire(EV_CLOSED, dev)
                elif state == G.MOVING:
                    self._fire(EV_MOVING, dev)
                    if direction == G.OPENING:
                        self._fire(EV_OPENING, dev)
                    elif direction == G.CLOSING:
                        self._fire(EV_CLOSING, dev)
                elif state == G.STUCK:
                    self.logger.warning(f"{dev.name}: stuck part-way")
                    self._fire(EV_STUCK, dev)
                self.logger.info(f"{dev.name}: {G.describe(state, direction=direction)}")

            self._apply_lamps(dev, state, props)
            self._mirror_homekit(dev, state, props)
        elif lamps_mode_changed:
            # No door change to ride on, so a change of Shadow Mode would leave
            # the lamps as they were until the door next moved.
            self._apply_lamps(dev, state, props, only_if_different=True)

        # --- sensor problems ---------------------------------------------
        # Said once when it starts or changes, not on every tick.
        if problem and problem != st.get("problem"):
            tail = "" if problem == G.CONTRADICTION else ", so the door's position is unknown"
            self.logger.warning(f"{dev.name}: {problem}{tail}")
            if not initial:
                self._fire(EV_SENSOR_FAULT, dev)
        elif not problem and st.get("problem"):
            self.logger.info(f"{dev.name}: the contact sensors are reporting again")
        st["problem"] = problem

        # --- states ------------------------------------------------------
        open_min = ((now - st["left_closed_at"]) / 60.0) if st["left_closed_at"] else 0.0
        self._set(dev, "doorState", G.published_state(state, direction))
        self._set(dev, "direction", direction)
        self._set(dev, "isOpen", state == G.OPEN)
        self._set(dev, "openDurationMinutes", int(open_min))
        self._set(dev, "sensorsHealthy", healthy)
        self._set(dev, "sensorProblem", problem)
        self._set(dev, "leftClosedAt",
                  self._stamp(st["left_closed_at"]) if st["left_closed_at"] else "")

        # The light is evaluated EVERY tick, not just on a door transition.
        # Presence changes minutes after the door settles — somebody walks in —
        # and gating this on a state change meant the light never came on for
        # them. _apply_light only sends a command when the answer changes.
        self._apply_light(dev, state, props)

        # --- the alarm ---------------------------------------------------
        away  = self._var_true(props.get("awayVariable"))
        night = self._var_true(props.get("nightVariable"))
        level, notify = G.alarm_decision(
            state, open_min, away, night, props,
            last_level=st["last_level"], last_notified_minutes=st["last_notified_min"])
        self._set(dev, "alertLevel", level)

        if notify:
            st["last_level"] = level
            st["last_notified_min"] = open_min
            self._set(dev, "lastAlertSent", self._stamp(now))
            msg = G.describe(state, open_min, away, night)
            self.logger.warning(f"{dev.name}: {msg}")
            self._fire(EV_STILL_OPEN if level == G.ALERT_URGENT else EV_LEFT_OPEN, dev)
        elif level != st["last_level"] and level == G.ALERT_NONE:
            st["last_level"] = level
        if st["last_notified_min"] is None:
            self._set(dev, "lastAlertSent", "")

    def _seed_opening(self, dev, st, state, now, bottom_changed, bottom_problem):
        """Start the left-open clock for a door that was already open at start.

        Until v1.11 this was always "now", so every plugin restart with the
        door open restarted the alarm and re-sent the first alert.
        """
        seed = st.get("seed") or {}
        # The bottom contact's own lastChanged only dates the opening when the
        # door is known to be off the bottom and that sensor is usable.
        usable = state in (G.OPEN, G.MOVING, G.STUCK) and not bottom_problem
        left, source = G.seed_left_closed_at(
            now, stored=seed.get("stored"), heartbeat=seed.get("heartbeat"),
            contact_changed=bottom_changed, contact_usable=usable)
        st["left_closed_at"] = left
        if source == "stored":
            # Same opening as before the restart: carry on where the alarm was.
            try:
                level = max(G.ALERT_NONE, min(G.ALERT_URGENT, int(seed.get("alert_level") or 0)))
            except (TypeError, ValueError):
                level = G.ALERT_NONE
            sent = seed.get("alert_sent")
            if level and sent is not None and left <= sent <= now + G.SEED_SKEW_S:
                st["last_level"] = level
                st["last_notified_min"] = max(0.0, (sent - left) / 60.0)
        if source != "now":
            how = ("the time saved before the restart" if source == "stored"
                   else "when the bottom sensor last changed")
            self.logger.info(f"{dev.name}: open since {self._clock(left)} "
                             f"(from {how})")

    def _set(self, dev, key, value):
        try:
            if dev.states.get(key) != value:
                dev.updateStateOnServer(key, value)
        except Exception as e:
            self.logger.debug(f"Could not write {key}: {e}")

    @staticmethod
    def _stamp(epoch=None):
        when = datetime.now() if epoch is None else datetime.fromtimestamp(epoch)
        return when.strftime(G.STAMP_FORMAT)

    @staticmethod
    def _clock(epoch):
        """A time as a person says it, e.g. 2:05pm."""
        t = datetime.fromtimestamp(epoch)
        hour = t.hour % 12 or 12
        return f"{hour}:{t.minute:02d}{'am' if t.hour < 12 else 'pm'}"

    # ------------------------------------------------------------------
    # Things that follow the door
    # ------------------------------------------------------------------

    def _warn_once(self, dev, key, message):
        """Say a configuration problem ONCE per plugin run, not on every close.

        Once per run rather than once ever: if it is still broken after a
        restart it is still worth saying, and a warning nobody ever sees again
        is how a silent fault stays silent.
        """
        st = self.doors.get(dev.id)
        seen = st.setdefault("warned", set()) if st is not None else self._warned_no_state
        if key in seen:
            return
        seen.add(key)
        self.logger.warning(f"{dev.name}: {message}")

    def _apply_light(self, dev, state, props):
        light_id = props.get("garageLightId")
        if not light_id:
            return
        present = self._state_of(props.get("presenceSensorId"), "onState", "occupancy", "motion")
        lux_id  = props.get("luxSensorId")
        lux     = self._state_of(lux_id, "illuminance", "sensorValue") if lux_id else None
        dark    = None
        if not lux_id and G.cfg_get(props, "lightOnlyIfDark"):
            # No light-level sensor: judge "dark" by the Dark variable. Without
            # this the light was switched off on every close but never on.
            night_var = props.get("nightVariable")
            dark = self._var_reading(night_var)
            if dark is None and night_var:
                self._warn_once(dev, "dark_var",
                                f"there is no light-level sensor and the \"Dark\" variable "
                                f"'{night_var}' cannot be read, so the garage light will come "
                                f"on whenever the door opens, day or night.")
        want = G.light_decision(state, present, lux, props,
                                dark=dark, lux_configured=bool(lux_id))
        if want is None:
            return                                  # no reading: leave it alone

        # light_want records a command that actually WENT. Until v1.11 it was
        # recorded before the command, so one that raised was never retried,
        # and in shadow mode it marked the light done — turning shadow mode
        # off then sent nothing until the answer next changed.
        st = self.doors.get(dev.id)
        if st is None:
            st = {}
        shadow = self._shadow_mode()
        if st.get("light_mode") != shadow:
            st["light_mode"] = shadow               # mode changed: reconcile
            st["light_want"] = None
        if st.get("light_want") == want:
            return                                  # already done, do not repeat
        word = "on" if want else "off"
        if shadow:
            st["light_want"] = want                 # in shadow, "done" = said so
            self.logger.debug(f"[shadow] would turn the garage light {word}")
            return
        failed_at = st.get("light_fail_at")
        if failed_at is not None and (time.time() - failed_at) < LIGHT_RETRY_SECONDS:
            return                                  # do not hammer a failing device
        try:
            indigo.device.turnOn(int(light_id)) if want else indigo.device.turnOff(int(light_id))
        except Exception as e:
            if failed_at is None:
                self.logger.error(f"Could not switch the garage light {word}: {e} "
                                  f"(trying again every {LIGHT_RETRY_SECONDS} seconds)")
            else:
                self.logger.debug(f"Garage light still not switching: {e}")
            st["light_fail_at"] = time.time()
            return
        if failed_at is not None:
            self.logger.info(f"{dev.name}: the garage light switched {word} after all")
        st["light_fail_at"] = None
        st["light_want"] = want

    def _apply_lamps(self, dev, state, props, only_if_different=False):
        """Drive the house lamps that announce the door.

        Ported from Garage_Door_Controller.py so the scripts can retire. Every
        device here is optional — a plugin carrying one house's decoration is no
        use to anyone else, so nothing fires unless it has been configured.

        only_if_different is the reconcile after Shadow Mode changes: a lamp
        already showing what it should is left alone, so nothing flashes.
        """
        hall_id = props.get("hallLampId")
        cons_id = props.get("conservatoryId")
        if not hall_id and not cons_id:
            return

        # Three cases, not two. No reference configured is a shut door with
        # nothing to restore to, so lamps off. A reference that reads is its own
        # answer. A reference that is CONFIGURED and cannot be read is neither —
        # and used to fall through to "off", which is how the restore branch
        # here had never once run on the install this was found on: the
        # reference still named a lamp that had been retired months earlier, so
        # every close switched the hall and conservatory lamps off instead.
        # Nothing was logged, because a missing device and a lamp that is off
        # are the same `None` to _state_of.
        ref_id = props.get("restoreReferenceId")
        if not ref_id:
            ref_on = None                       # nothing configured
        else:
            ref_on = G.as_reed(self._state_of(ref_id, "onState"))
            if ref_on is None:
                ref_on = G.REF_UNKNOWN
                self._warn_once(dev, "restore_ref",
                                f"the restore reference (device {ref_id}) cannot be read — "
                                f"it may have been deleted. Leaving the hall and conservatory "
                                f"lamps alone on close until it is fixed or cleared in the "
                                f"door's settings.")
        plan = G.lamp_plan(state, ref_on, props)

        if self._shadow_mode():
            self.logger.debug(f"[shadow] would set lamps: {plan}")
            return

        want = plan.get("hall")
        if hall_id and want:
            try:
                lamp = indigo.devices[int(hall_id)]
                if want == G.HALL_OFF:
                    if not (only_if_different and self._lamp_is_off(lamp)):
                        indigo.device.turnOff(lamp)
                else:
                    key = {G.HALL_MOVING: "hallColourMoving",
                           G.HALL_OPEN:   "hallColourOpen",
                           G.HALL_RESTORE: "hallColourRestore"}[want]
                    r, g, b = G.parse_rgb(props.get(key), _LAMP_FALLBACK[want])
                    if not (only_if_different and self._lamp_shows(lamp, (r, g, b))):
                        kw = {"redLevel": r, "greenLevel": g, "blueLevel": b}
                        if want == G.HALL_RESTORE:
                            try:
                                wt = int(props.get("hallRestoreWhiteTemp") or 3000)
                                kw["whiteTemperature"] = wt
                            except (TypeError, ValueError):
                                pass
                        indigo.dimmer.setColorLevels(lamp, **kw)
                        indigo.dimmer.setBrightness(lamp, 100)
            except Exception as e:
                self.logger.error(f"Hall lamp: {e}")

        want_c = plan.get("conservatory")
        if cons_id and want_c is not None:
            try:
                if only_if_different and self._state_of(cons_id, "onState") is want_c:
                    return
                indigo.device.turnOn(int(cons_id)) if want_c else indigo.device.turnOff(int(cons_id))
            except Exception as e:
                self.logger.error(f"Conservatory lamp: {e}")

    @staticmethod
    def _lamp_is_off(lamp):
        return getattr(lamp, "onState", None) is False

    @staticmethod
    def _lamp_shows(lamp, rgb):
        """True when the lamp is on at full brightness in exactly this colour.

        A level that cannot be read counts as different, so the reconcile
        errs towards putting the lamp right rather than leaving it wrong.
        """
        if getattr(lamp, "onState", None) is not True:
            return False
        if getattr(lamp, "brightness", None) != 100:
            return False
        try:
            have = (int(lamp.redLevel), int(lamp.greenLevel), int(lamp.blueLevel))
        except (AttributeError, TypeError, ValueError):
            return False
        return have == tuple(rgb)

    def _mirror_homekit(self, dev, state, props):
        var = props.get("homekitVariable")
        if not var:
            return
        value = G.homekit_value(state, G.as_bool(props.get("homekitInvert"), True))
        if value is None:
            return                                  # never claim shut when unsure
        try:
            indigo.variable.updateValue(
                indigo.variables[str(var)].id, str(value))   # variables take STRINGS
        except Exception as e:
            self.logger.error(f"Could not update the HomeKit variable: {e}")

    # ------------------------------------------------------------------
    # runConcurrentThread — the thing scripts could never do
    # ------------------------------------------------------------------

    def runConcurrentThread(self):
        try:
            while True:
                # The WHOLE body is guarded. One bad door must not stop the
                # others, and must not kill the loop that runs the alarm.
                for dev_id in list(self.doors.keys()):
                    try:
                        self._evaluate(dev_id)
                    except Exception as e:
                        self.logger.error(f"Door tick failed: {e}")
                self.sleep(TICK_SECONDS)
        except self.StopThread:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _pulse(self, dev, reason):
        """Fire the momentary relay. Direction is decided by the opener, not us."""
        st = self.doors.get(dev.id)
        props = st["props"] if st else dict(dev.pluginProps)
        now = time.time()

        debounce = G.debounce_seconds(props)
        if st and debounce and (now - st["last_pulse_at"]) < debounce:
            self.logger.warning(f"{dev.name}: ignoring a repeat operation within "
                                f"{debounce}s of the last one")
            return False

        relay_id = props.get("relayId")
        if not relay_id:
            self.logger.error(f"{dev.name}: no relay configured, cannot operate the door")
            return False

        if self._shadow_mode():
            self.logger.warning(f"[shadow] {dev.name}: would pulse the relay ({reason}). "
                                "Turn off Shadow Mode in the plugin config to enable control.")
            return False

        pulse_s = G.pulse_seconds(props)
        try:
            indigo.device.turnOn(int(relay_id))
            self.sleep(pulse_s)
            indigo.device.turnOff(int(relay_id))
        except Exception as e:
            self.logger.error(f"{dev.name}: relay pulse failed — {e}")
            try:
                indigo.device.turnOff(int(relay_id))   # never leave it energised
            except Exception:
                pass
            return False

        if st:
            st["last_pulse_at"] = now
            st["operated_by"] = reason
        self._set(dev, "lastOperatedBy", reason)
        self.logger.info(f"{dev.name}: pulsed the door relay ({reason})")
        return True

    def _door_for(self, action):
        try:
            return indigo.devices[action.deviceId]
        except (KeyError, AttributeError):
            self.logger.error("Action was not aimed at a garage door device")
            return None

    def actionOpenDoor(self, action):
        dev = self._door_for(action)
        if not dev:
            return
        st = self.doors.get(dev.id, {})
        if st.get("state") == G.OPEN:
            self.logger.info(f"{dev.name}: already open, nothing to do")
            return                                    # idempotent, per the spec
        if self._refuse_unknown(dev, st, "open"):
            return
        self._pulse(dev, action.props.get("source") or "action:open")

    def actionCloseDoor(self, action):
        dev = self._door_for(action)
        if not dev:
            return
        st = self.doors.get(dev.id, {})
        if st.get("state") == G.CLOSED:
            self.logger.info(f"{dev.name}: already closed, nothing to do")
            return
        if self._refuse_unknown(dev, st, "close"):
            return
        self._pulse(dev, action.props.get("source") or "action:close")

    def _refuse_unknown(self, dev, st, verb):
        """Open and Close do nothing while the position is unknown.

        The opener has one button: a press on a door we cannot see might do the
        opposite of what was asked. Toggle and Pulse Relay are a deliberate
        press of that button, so they still work.
        """
        if st.get("state") not in (None, G.UNKNOWN):
            return False
        why = st.get("problem") or "the door's position is unknown"
        self.logger.warning(f"{dev.name}: not asked to {verb} — {why}. "
                            "Use Toggle if you mean to press the button anyway.")
        return True

    def actionToggleDoor(self, action):
        dev = self._door_for(action)
        if dev:
            self._pulse(dev, action.props.get("source") or "action:toggle")

    def actionPulseRelay(self, action):
        dev = self._door_for(action)
        if dev:
            self._pulse(dev, action.props.get("source") or "action:pulse")

    def actionRefreshState(self, action):
        dev = self._door_for(action)
        if dev:
            self._evaluate(dev.id)
            note = str(action.props.get("source") or "").strip()
            line = f"{dev.name}: {G.describe(self.doors.get(dev.id, {}).get('state'))}"
            self.logger.info(f"{line} ({note})" if note else line)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def _extras(self):
        mode = "SHADOW (read-only)" if self._shadow_mode() else "control enabled"
        return [("Mode:", mode), ("Doors:", str(len(self.doors)))]

    def showPluginInfo(self, valuesDict=None, typeId=None):
        if log_startup_banner:
            log_startup_banner(self.pluginId, self.pluginDisplayName,
                               self.pluginVersion, extras=self._extras())
        else:
            indigo.server.log(f"{self.pluginDisplayName} v{self.pluginVersion}")

    def menuTestSetup(self, valuesDict=None, typeId=None):
        """Full environment plus a PASS/FAIL sweep — one block to paste into a
        support post when something is not behaving."""
        if log_startup_banner:
            log_startup_banner(self.pluginId, self.pluginDisplayName,
                               self.pluginVersion, extras=self._extras())
        if not self.doors:
            self.logger.error("FAIL  no garage door devices exist yet")
            return
        for dev_id, st in self.doors.items():
            try:
                dev = indigo.devices[dev_id]
            except KeyError:
                continue
            p = st["props"]
            self.logger.info(f"--- {dev.name} ---")
            for label, key, state_key in (
                    ("bottom contact", "bottomContactId", "contact"),
                    ("top contact",    "topContactId",    "contact"),
                    ("relay",          "relayId",         None),
                    ("presence",       "presenceSensorId", None),
                    ("lux",            "luxSensorId",     None),
                    ("garage light",   "garageLightId",   None),
                    ("signal lamp",    "hallLampId",      None),
                    ("second lamp",    "conservatoryId",  None),
                    ("restore reference", "restoreReferenceId", "onState")):
                dev_ref = p.get(key)
                if not dev_ref:
                    self.logger.info(f"  ----  {label}: not set")
                    continue
                try:
                    d = indigo.devices[int(dev_ref)]
                except (KeyError, ValueError, TypeError):
                    self.logger.error(f"  FAIL  {label}: device {dev_ref} does not exist")
                    continue
                extra = ""
                if key == "hallLampId" and getattr(d, "supportsRGB", True) is False:
                    self.logger.error(f"  FAIL  {label}: {d.name} cannot show colours")
                    continue
                if state_key:
                    v = getattr(d, "onState", None) if state_key == "onState" \
                        else d.states.get(state_key)
                    extra = f" ({state_key}={v!r})"
                    if v is None:
                        self.logger.error(f"  FAIL  {label}: {d.name} has no "
                                          f"'{state_key}' state")
                        continue
                self.logger.info(f"  PASS  {label}: {d.name}{extra}")
            for label, key in (("away variable", "awayVariable"),
                               ("night variable", "nightVariable"),
                               ("HomeKit variable", "homekitVariable")):
                ref = p.get(key)
                if not ref:
                    self.logger.info(f"  ----  {label}: not set")
                    continue
                try:
                    v = indigo.variables[str(ref)]
                    self.logger.info(f"  PASS  {label}: {v.name} = {v.value!r}")
                except (KeyError, ValueError):
                    self.logger.error(f"  FAIL  {label}: '{ref}' not found by name")
            self.logger.info(f"  state: {G.describe(st.get('state'))}")
        self.logger.info("SHADOW MODE is ON — the plugin will not operate the door"
                         if self._shadow_mode() else
                         "Shadow mode is OFF — the plugin WILL operate the door")

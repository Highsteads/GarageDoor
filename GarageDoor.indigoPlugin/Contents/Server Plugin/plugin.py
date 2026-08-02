#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    plugin.py
# Description: One Indigo device that owns the garage door — its real position,
#              how long it has been open, the alarm when it is left that way,
#              and the light that follows whoever walked in.
# Author:      CliveS & Claude Opus 5
# Date:        02-08-2026
# Version:     1.0
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

# Events declared in Events.xml
EV_OPENED       = "doorOpened"
EV_CLOSED       = "doorClosed"
EV_MOVING       = "doorStartedMoving"
EV_LEFT_OPEN    = "doorLeftOpen"
EV_STILL_OPEN   = "doorStillOpen"
EV_STUCK        = "doorStuck"
EV_SENSOR_FAULT = "sensorFault"


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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def startup(self):
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
        mode = "SHADOW MODE (not operating the door)" if self._shadow_mode() \
            else "door control ENABLED"
        self.logger.info(f"Configuration saved — now in {mode}")

    def _shadow_mode(self):
        return G.as_bool(self.pluginPrefs.get("shadowMode"), True)

    # ------------------------------------------------------------------
    # Device lifecycle
    # ------------------------------------------------------------------

    def deviceStartComm(self, dev):
        props = dict(dev.pluginProps)
        self.doors[dev.id] = {
            "props": props,
            "state": None,
            "left_closed_at": None,     # when it stopped being shut
            "moving_since": None,       # when it left a known position
            "last_level": G.ALERT_NONE,
            "last_notified_min": None,
            "last_pulse_at": 0.0,
            "operated_by": "",
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

        bottom = self._state_of(props.get("bottomContactId"), "contact")
        top    = self._state_of(props.get("topContactId"), "contact")

        moving_for = (now - st["moving_since"]) if st["moving_since"] else 0.0
        state, healthy = G.derive_state(bottom, top, moving_for, props)

        previous = st["state"]
        st["state"] = state

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
                elif state == G.STUCK:
                    self.logger.warning(f"{dev.name}: stuck part-way")
                    self._fire(EV_STUCK, dev)
                self.logger.info(f"{dev.name}: {G.describe(state)}")

            self._apply_light(dev, state, props)
            self._mirror_homekit(dev, state, props)

        if not healthy and previous is not None and state != previous:
            self.logger.warning(f"{dev.name}: both contact sensors report the door "
                                "is at their end, which cannot both be true")
            self._fire(EV_SENSOR_FAULT, dev)

        # --- states ------------------------------------------------------
        open_min = ((now - st["left_closed_at"]) / 60.0) if st["left_closed_at"] else 0.0
        self._set(dev, "doorState", state)
        self._set(dev, "isOpen", state == G.OPEN)
        self._set(dev, "openDurationMinutes", int(open_min))
        self._set(dev, "sensorsHealthy", healthy)

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
            msg = G.describe(state, open_min, away, night)
            self.logger.warning(f"{dev.name}: {msg}")
            self._fire(EV_STILL_OPEN if level == G.ALERT_URGENT else EV_LEFT_OPEN, dev)
        elif level != st["last_level"] and level == G.ALERT_NONE:
            st["last_level"] = level

    def _set(self, dev, key, value):
        try:
            if dev.states.get(key) != value:
                dev.updateStateOnServer(key, value)
        except Exception as e:
            self.logger.debug(f"Could not write {key}: {e}")

    @staticmethod
    def _stamp():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Things that follow the door
    # ------------------------------------------------------------------

    def _apply_light(self, dev, state, props):
        light_id = props.get("garageLightId")
        if not light_id:
            return
        present = self._state_of(props.get("presenceSensorId"), "onState", "occupancy", "motion")
        lux     = self._state_of(props.get("luxSensorId"), "illuminance", "sensorValue")
        want = G.light_decision(state, present, lux, props)
        if want is None:
            return                                  # no reading: leave it alone
        try:
            if self._shadow_mode():
                self.logger.debug(f"[shadow] would turn the garage light "
                                  f"{'on' if want else 'off'}")
                return
            indigo.device.turnOn(int(light_id)) if want else indigo.device.turnOff(int(light_id))
        except Exception as e:
            self.logger.error(f"Could not switch the garage light: {e}")

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

        debounce = G.cfg_get(props, "operationDebounceSeconds") or 5
        if st and (now - st["last_pulse_at"]) < debounce:
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

        try:
            pulse_ms = int(G.cfg_get(props, "pulseMilliseconds") or 1000)
        except (TypeError, ValueError):
            pulse_ms = 1000
        try:
            indigo.device.turnOn(int(relay_id))
            self.sleep(pulse_ms / 1000.0)
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
        self._pulse(dev, action.props.get("source") or "action:open")

    def actionCloseDoor(self, action):
        dev = self._door_for(action)
        if not dev:
            return
        st = self.doors.get(dev.id, {})
        if st.get("state") == G.CLOSED:
            self.logger.info(f"{dev.name}: already closed, nothing to do")
            return
        self._pulse(dev, action.props.get("source") or "action:close")

    def actionToggleDoor(self, action):
        dev = self._door_for(action)
        if dev:
            self._pulse(dev, action.props.get("source") or "action:toggle")

    def actionPulseRelay(self, action):
        dev = self._door_for(action)
        if dev:
            self._pulse(dev, "action:pulse")

    def actionRefreshState(self, action):
        dev = self._door_for(action)
        if dev:
            self._evaluate(dev.id)
            self.logger.info(f"{dev.name}: {G.describe(self.doors.get(dev.id, {}).get('state'))}")

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
                    ("garage light",   "garageLightId",   None)):
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
                if state_key:
                    v = d.states.get(state_key)
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

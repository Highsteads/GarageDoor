#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_plugin_smoke.py
# Description: Loads plugin.py against a stubbed Indigo and drives a whole door
#              cycle, so a typo in the plugin is caught here rather than by a
#              restart that fails to start.
# Author:      CliveS & Claude Opus 5
# Date:        02-08-2026
# Version:     1.0
#
# WHY: garage_logic.py is pure and thoroughly tested, but the plugin around it
# is where the Indigo API is used, and none of that runs without a server. A
# stub is enough to prove the module imports, the class constructs, the device
# lifecycle runs, states get written, events fire and — the one that matters —
# that SHADOW MODE never sends a command to the relay.

import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "GarageDoor.indigoPlugin", "Contents", "Server Plugin")


# ── the smallest Indigo that will hold still ──────────────────────────

class FakeDevice:
    def __init__(self, dev_id, name, states=None, plugin_id="other.plugin", props=None):
        self.id = dev_id
        self.name = name
        self.states = dict(states or {})
        self.pluginId = plugin_id
        self.pluginProps = dict(props or {})
        self.onState = self.states.get("onState")
        self.written = []

    def updateStateOnServer(self, key, value):
        self.states[key] = value
        self.written.append((key, value))


class FakeVariable:
    def __init__(self, var_id, name, value):
        self.id, self.name, self.value = var_id, name, value


class FakeCollection(dict):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._by_name = {}

    def add(self, obj):
        self[obj.id] = obj
        self._by_name[obj.name] = obj

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self._by_name:
                return self._by_name[key]
            if key.isdigit() and int(key) in self:
                return dict.__getitem__(self, int(key))
            raise KeyError(key)
        return dict.__getitem__(self, key)

    def __iter__(self):
        return iter(list(self.values()))

    def iter(self, _filter=None):
        return iter([])

    @staticmethod
    def subscribeToChanges():
        return None


def build_indigo():
    ind = types.ModuleType("indigo")
    ind.devices = FakeCollection()
    ind.variables = FakeCollection()
    ind.commands = []

    class PluginBase:
        StopThread = type("StopThread", (Exception,), {})

        def __init__(self, pid, name, version, prefs):
            self.pluginId, self.pluginDisplayName = pid, name
            self.pluginVersion, self.pluginPrefs = version, dict(prefs)
            import logging
            self.logger = logging.getLogger("garagedoor.test")
            self.logger.addHandler(logging.NullHandler())

        def sleep(self, _s):
            return None

        def deviceUpdated(self, *_a):
            return None

    ind.PluginBase = PluginBase

    dev_ns = types.SimpleNamespace(
        turnOn=lambda i: ind.commands.append(("on", int(i))),
        turnOff=lambda i: ind.commands.append(("off", int(i))),
    )
    ind.device = dev_ns
    ind.variable = types.SimpleNamespace(
        updateValue=lambda vid, val: ind.commands.append(("var", vid, val)))
    ind.trigger = types.SimpleNamespace(
        execute=lambda t: ind.commands.append(("trigger", t.pluginTypeId)))
    ind.server = types.SimpleNamespace(log=lambda *a, **k: None)
    return ind


@pytest.fixture()
def plugin(monkeypatch):
    ind = build_indigo()
    monkeypatch.setitem(sys.modules, "indigo", ind)
    monkeypatch.syspath_prepend(SRC)
    for mod in ("plugin", "garage_logic", "plugin_utils"):
        sys.modules.pop(mod, None)
    import plugin as plugin_mod
    monkeypatch.setattr(plugin_mod, "indigo", ind, raising=False)

    ind.devices.add(FakeDevice(101, "Bottom Contact", {"contact": True}))
    ind.devices.add(FakeDevice(102, "Top Contact", {"contact": False}))
    ind.devices.add(FakeDevice(103, "Door Relay", {"onOffState": False}))
    ind.devices.add(FakeDevice(104, "Garage Light", {"onOffState": False}))
    ind.devices.add(FakeDevice(105, "Presence", {"onState": True}))
    ind.devices.add(FakeDevice(106, "Lux", {"illuminance": 3}))
    ind.variables.add(FakeVariable(201, "Away", "false"))
    ind.variables.add(FakeVariable(202, "Nightime", "false"))
    ind.variables.add(FakeVariable(203, "garage_door_state", "on"))

    door = FakeDevice(1, "Garage Door", plugin_id="com.clives.indigoplugin.garagedoor",
                      props={
                          "bottomContactId": "101", "topContactId": "102",
                          "relayId": "103", "garageLightId": "104",
                          "presenceSensorId": "105", "luxSensorId": "106",
                          "awayVariable": "Away", "nightVariable": "Nightime",
                          "homekitVariable": "garage_door_state",
                          "pulseMilliseconds": "1000",
                      })
    ind.devices.add(door)

    p = plugin_mod.Plugin("com.clives.indigoplugin.garagedoor", "Garage Door", "1.0",
                          {"shadowMode": "true"})
    return p, ind, door, plugin_mod


# ── the tests ─────────────────────────────────────────────────────────

def test_the_plugin_starts_and_reads_a_closed_door(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    assert door.states["doorState"] == "closed"
    assert door.states["isOpen"] is False
    assert door.states["sensorsHealthy"] is True


def test_an_unconfigured_door_does_not_crash(plugin):
    """Every install begins with nothing filled in."""
    p, ind, _, _ = plugin
    blank = FakeDevice(9, "New Door",
                       plugin_id="com.clives.indigoplugin.garagedoor", props={})
    ind.devices.add(blank)
    p.startup()
    p.deviceStartComm(blank)           # must not raise
    assert blank.states["doorState"] == "unknown"


def test_a_full_open_cycle_writes_states_and_fires_events(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)

    trig = types.SimpleNamespace(id=7, name="t", pluginTypeId="doorOpened",
                                 pluginProps={})
    p.triggerStartProcessing(trig)

    ind.devices[101].states["contact"] = False        # leaves the bottom
    p._evaluate(door.id)
    assert door.states["doorState"] == "moving"

    ind.devices[102].states["contact"] = True         # reaches the top
    p._evaluate(door.id)
    assert door.states["doorState"] == "open"
    assert door.states["isOpen"] is True
    assert ("trigger", "doorOpened") in ind.commands
    assert door.states["lastOpened"]


def test_shadow_mode_never_touches_the_relay(plugin):
    """The single most important guarantee in v1.0."""
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    ind.commands.clear()

    action = types.SimpleNamespace(deviceId=door.id, props={})
    p.actionToggleDoor(action)
    p.actionOpenDoor(action)
    p.actionPulseRelay(action)

    relay_cmds = [c for c in ind.commands if c[0] in ("on", "off") and c[1] == 103]
    assert relay_cmds == [], f"shadow mode sent commands to the relay: {relay_cmds}"


def test_with_shadow_off_the_relay_is_pulsed_and_released(plugin):
    p, ind, door, _ = plugin
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()
    p.deviceStartComm(door)
    ind.commands.clear()

    p.actionToggleDoor(types.SimpleNamespace(deviceId=door.id, props={}))
    relay = [c for c in ind.commands if c[1] == 103]
    assert relay == [("on", 103), ("off", 103)], relay


def test_the_relay_is_released_even_when_the_off_command_is_late(plugin):
    """A failed release leaves a door relay energised — it must always try."""
    p, ind, door, _ = plugin
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()
    p.deviceStartComm(door)
    ind.commands.clear()

    calls = {"n": 0}
    original = ind.device.turnOff

    def flaky(i):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        original(i)

    ind.device.turnOff = flaky
    p.actionToggleDoor(types.SimpleNamespace(deviceId=door.id, props={}))
    assert ("off", 103) in ind.commands


def test_opening_an_already_open_door_does_nothing(plugin):
    p, ind, door, _ = plugin
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()
    ind.devices[101].states["contact"] = False
    ind.devices[102].states["contact"] = True
    p.deviceStartComm(door)
    ind.commands.clear()

    p.actionOpenDoor(types.SimpleNamespace(deviceId=door.id, props={}))
    assert [c for c in ind.commands if c[1] == 103] == []


def test_a_repeat_press_inside_the_debounce_is_dropped(plugin):
    p, ind, door, _ = plugin
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()
    p.deviceStartComm(door)
    ind.commands.clear()

    a = types.SimpleNamespace(deviceId=door.id, props={})
    p.actionToggleDoor(a)
    p.actionToggleDoor(a)
    assert len([c for c in ind.commands if c == ("on", 103)]) == 1


def test_our_own_device_updates_do_not_re_enter(plugin):
    """Without the loop guard, writing a state re-enters deviceUpdated forever."""
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    p.deviceUpdated(door, door)        # our own plugin id — must return at once


def test_homekit_variable_is_written_inverted(plugin):
    p, ind, door, _ = plugin
    p.startup()
    p.deviceStartComm(door)
    ind.commands.clear()
    ind.devices[101].states["contact"] = False
    ind.devices[102].states["contact"] = True
    p._evaluate(door.id)
    var_writes = [c for c in ind.commands if c[0] == "var"]
    assert var_writes and var_writes[-1][2] == "off"   # open -> "off"
    assert isinstance(var_writes[-1][2], str)          # variables take STRINGS


def test_the_light_follows_presence_not_just_the_door(plugin):
    """The bug a real door found: _apply_light only ran on a state change, so
    walking into the garage a minute after it opened never lit anything."""
    p, ind, door, _ = plugin
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()
    ind.devices[105].states["onState"] = False      # nobody there yet
    ind.devices[105].onState = False
    ind.devices[101].states["contact"] = False      # door open
    ind.devices[102].states["contact"] = True
    p.deviceStartComm(door)
    ind.commands.clear()

    p._evaluate(door.id)                            # settled, still empty
    assert [c for c in ind.commands if c[1] == 104] == []

    ind.devices[105].states["onState"] = True       # somebody walks in
    ind.devices[105].onState = True
    p._evaluate(door.id)                            # no door change at all
    assert ("on", 104) in ind.commands, "the light should follow presence"


def test_the_light_is_not_commanded_over_and_over(plugin):
    """Every tick evaluates it, but only a change is sent."""
    p, ind, door, _ = plugin
    p.pluginPrefs["shadowMode"] = "false"
    p.startup()
    ind.devices[101].states["contact"] = False
    ind.devices[102].states["contact"] = True
    p.deviceStartComm(door)
    ind.commands.clear()
    for _ in range(10):
        p._evaluate(door.id)
    light = [c for c in ind.commands if c[1] == 104]
    assert len(light) <= 1, f"light commanded {len(light)} times for one state"

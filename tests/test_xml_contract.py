#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_xml_contract.py
# Description: The plugin's XML files against plugin.py. Indigo only reads
#              Actions/MenuItems/Events/Devices XML when someone opens a dialog
#              or runs an action, so a misspelt callback or a state that was
#              never declared fails silently on the Mac, not at start-up.
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.0
#
# Ported in spirit from ApplianceMonitor's test_config_xml.py and
# test_actions_and_menus.py, cut down to what this plugin actually uses.

import collections
import glob
import os
import re
import xml.etree.ElementTree as ET

import pytest

from conftest import ROOT, SRC

XML_FILES = sorted(glob.glob(os.path.join(SRC, "*.xml")))
PLUGIN_PY = os.path.join(SRC, "plugin.py")


def _root(name):
    return ET.parse(os.path.join(SRC, name)).getroot()


def _plugin_source():
    with open(PLUGIN_PY, encoding="utf-8") as fh:
        return fh.read()


def _plugin_methods():
    """Method names defined on the Plugin class, read from the source.

    Read as text rather than imported so the check works with no Indigo at all.
    """
    return set(re.findall(r"^    def (\w+)\(", _plugin_source(), flags=re.M))


# ── every file parses, and the glob found them ─────────────────────────

def test_the_xml_files_were_found():
    # A glob that matches nothing would make every test below pass.
    names = {os.path.basename(p) for p in XML_FILES}
    assert {"Actions.xml", "Devices.xml", "Events.xml",
            "MenuItems.xml", "PluginConfig.xml"} <= names


@pytest.mark.parametrize("path", XML_FILES, ids=os.path.basename)
def test_every_xml_file_parses(path):
    ET.parse(path)


def test_info_plist_parses():
    ET.parse(os.path.join(ROOT, "GarageDoor.indigoPlugin", "Contents", "Info.plist"))


# ── named methods exist ────────────────────────────────────────────────

def _named_callbacks():
    """Every method name an XML file asks Indigo to call on the plugin."""
    found = []
    for path in XML_FILES:
        root = ET.parse(path).getroot()
        for el in root.iter("CallbackMethod"):
            found.append((os.path.basename(path), (el.text or "").strip()))
        for el in root.iter():
            # <List class="self" method="..."> and the button/field callbacks.
            for attr in ("method", "callbackMethod"):
                if el.get(attr) and (attr != "method" or el.get("class") == "self"):
                    found.append((os.path.basename(path), el.get(attr)))
            if el.tag == "ButtonCallback":
                found.append((os.path.basename(path), (el.text or "").strip()))
    return found


def test_there_are_callbacks_to_check():
    assert len(_named_callbacks()) >= 5


def test_every_callback_named_in_the_xml_exists_in_plugin_py():
    methods = _plugin_methods()
    missing = [(f, m) for f, m in _named_callbacks() if m not in methods]
    assert missing == [], f"XML names methods plugin.py does not define: {missing}"


# ── ids and bindings ───────────────────────────────────────────────────

def _scopes(path):
    root = ET.parse(path).getroot()
    if os.path.basename(path) == "PluginConfig.xml":
        return [root]
    return list(root.iter("ConfigUI")) or [root]


@pytest.mark.parametrize("path", XML_FILES, ids=os.path.basename)
def test_field_ids_are_present_and_unique_in_each_dialog(path):
    for scope in _scopes(path):
        ids = [f.get("id") for f in scope.iter("Field")]
        assert all(ids), f"{os.path.basename(path)}: a Field with no id"
        dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
        assert dupes == [], f"{os.path.basename(path)}: duplicate Field ids {dupes}"


@pytest.mark.parametrize("path", XML_FILES, ids=os.path.basename)
def test_visible_bindings_point_at_a_field_in_the_same_dialog(path):
    for scope in _scopes(path):
        ids = {f.get("id") for f in scope.iter("Field")}
        for f in scope.iter("Field"):
            b = f.get("visibleBindingId")
            if b:
                assert b in ids, f"{f.get('id')} binds to missing field {b}"


def test_action_and_event_device_filters_name_a_real_device_type():
    device_ids = {d.get("id") for d in _root("Devices.xml").iter("Device")}
    filters = []
    for name in ("Actions.xml", "Events.xml"):
        for el in _root(name).iter():
            for attr in ("deviceFilter", "filter"):
                v = el.get(attr)
                if v and v.startswith("self."):
                    filters.append(v)
    assert filters, "no self.* filters found — the check is not checking"
    for v in filters:
        assert v.split(".", 1)[1] in device_ids, f"{v} is not a device in Devices.xml"


def test_get_door_list_iterates_the_declared_device_type():
    device_ids = {d.get("id") for d in _root("Devices.xml").iter("Device")}
    for m in re.findall(r'devices\.iter\("self\.(\w+)"\)', _plugin_source()):
        assert m in device_ids


# ── events and states ──────────────────────────────────────────────────

def test_every_event_the_plugin_fires_is_declared_and_vice_versa():
    """A fired id with no <Event> runs no trigger; an <Event> never fired is a
    trigger the user can create that will never run."""
    declared = {e.get("id") for e in _root("Events.xml").iter("Event")}
    fired = set(re.findall(r'^EV_\w+\s*=\s*"(\w+)"', _plugin_source(), flags=re.M))
    assert fired, "no EV_ constants found"
    assert fired == declared


def test_every_state_the_plugin_writes_is_declared_in_devices_xml():
    """_set() swallows its exceptions at DEBUG, so a write to an undeclared
    state would vanish without a word in the Event Log."""
    declared = {s.get("id") for s in _root("Devices.xml").iter("State")}
    written = set(re.findall(r'_set\(dev,\s*"(\w+)"', _plugin_source()))
    assert written, "no _set() calls found — the check is not checking"
    assert written - declared == set()


def test_every_device_prop_the_plugin_reads_is_a_field_in_devices_xml():
    """A props.get("someKey") with no matching Field always reads None."""
    fields = {f.get("id") for f in _root("Devices.xml").iter("Field")}
    src = _plugin_source()
    read = set(re.findall(r'(?<!action\.)props\.get\("(\w+)"', src))
    read |= set(re.findall(r'\("[^"]+",\s*"(\w+Id)",\s*(?:"\w+"|None)\)', src))
    assert read, "no props.get() calls found"
    assert read - fields == set()


def test_every_action_prop_the_plugin_reads_is_a_field_in_actions_xml():
    fields = {f.get("id") for f in _root("Actions.xml").iter("Field")}
    read = set(re.findall(r'action\.props\.get\("(\w+)"', _plugin_source()))
    assert read, "no action.props.get() calls found"
    assert read - fields == set()


def test_door_state_list_offers_every_state_the_plugin_publishes():
    import importlib
    import sys
    sys.path.insert(0, SRC)
    try:
        G = importlib.import_module("garage_logic")
    finally:
        sys.path.remove(SRC)
    door_state = [s for s in _root("Devices.xml").iter("State")
                  if s.get("id") == "doorState"][0]
    options = {o.get("value") for o in door_state.iter("Option")}
    published = {G.published_state(s, d)
                 for s in (G.CLOSED, G.OPEN, G.MOVING, G.STUCK, G.UNKNOWN)
                 for d in (G.OPENING, G.CLOSING, G.NO_DIRECTION)}
    assert published <= options


# ── changelog ──────────────────────────────────────────────────────────

def test_the_changelog_has_an_entry_for_this_version():
    import plistlib
    with open(os.path.join(ROOT, "GarageDoor.indigoPlugin", "Contents", "Info.plist"),
              "rb") as fh:
        version = plistlib.load(fh)["PluginVersion"]
    with open(os.path.join(ROOT, "docs", "changelog.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert re.search(rf"^##\s+{re.escape(version)}\b", text, flags=re.M), \
        f"docs/changelog.md has no '## {version}' heading"

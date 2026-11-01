#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    conftest.py
# Description: Shared test seam for Garage Door. Puts the plugin bundle on the
#              import path and makes the stubbed-Indigo `plugin` fixture (built
#              in test_plugin_smoke.py) available to every test file, so new
#              tests drive the same fake Indigo instead of growing a second one.
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.0
#
# WHY NOT A NEW STUB HERE: test_plugin_smoke.py already holds a careful fake
# Indigo (devices, variables, relay commands, triggers). Two fakes drift apart,
# and the one that drifts is the one nobody looks at. This file only re-exports
# it. The fixture installs `indigo` into sys.modules per test, so plugin.py is
# imported fresh every time without a real Indigo server.

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "GarageDoor.indigoPlugin", "Contents", "Server Plugin")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Re-exported so any test file can ask for `plugin`. The smoke file's own
# definition is the same object, so nothing is defined twice.
from test_plugin_smoke import plugin  # noqa: E402,F401

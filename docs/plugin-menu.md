---
title: The plugin menu
nav_order: 8
---

# The plugin menu

These are under **Plugins → Garage Door**.

| Menu item | What it does |
|---|---|
| **Test Garage Door Setup** | Checks every door's settings and writes the result to the Event Log. For each door it lists the bottom and top sensors, the relay, the presence sensor, the light-level sensor and the garage light, then the away, dark and HomeKit variables. Each one shows **PASS** with its name if the plugin can find it, **FAIL** if it cannot, or `----` if you have left it blank. For the two sensors it also shows the current reading, and says **FAIL** if the sensor has no **contact** state. It ends with where each door is now, and whether Shadow Mode is on. It does not check the lamps in the house. |
| **Show Plugin Info** | Writes the plugin's version, whether it is in Shadow Mode, how many doors it looks after, and details of your Mac and Indigo to the Event Log. This is useful to include if you ask for help on the Indigo forum. |

**Test Garage Door Setup** also writes the same details as **Show Plugin Info** first, so its output is the one to copy if you ask for help.

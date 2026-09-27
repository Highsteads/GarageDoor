---
title: The plugin menu
nav_order: 8
---

# The plugin menu

These are under **Plugins → Garage Door**.

| Menu item | What it does |
|---|---|
| **Test Garage Door Setup** | Checks every door's settings and writes the result to the Event Log. For each door it lists the bottom and top sensors, the relay, the presence sensor, the light-level sensor, the garage light, the signal lamp, the second lamp and the reference lamp, then the away, dark and HomeKit variables. Each one shows **PASS** with its name if the plugin can find it, **FAIL** if it cannot, or `----` if you have left it blank. For the two sensors it also shows the current reading, and says **FAIL** if the sensor has no **contact** state. It shows whether the reference lamp is on, says **FAIL** if it cannot tell, and says **FAIL** if the signal lamp cannot show colours. It ends with where each door is now, and whether Shadow Mode is on. |
| **Show Plugin Info** | Writes the plugin's version, whether it is in Shadow Mode, how many doors it looks after, and details of your Mac and Indigo to the Event Log. This is useful to include if you ask for help on the Indigo forum. |

**Test Garage Door Setup** also writes the same details as **Show Plugin Info** first, so its output is the one to copy if you ask for help.

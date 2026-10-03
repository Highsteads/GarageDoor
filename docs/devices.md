---
title: Your garage door
nav_order: 4
---

# Your garage door

The plugin has one kind of device, **Garage Door**, and each one looks after one door.

The device is not a switch, so it has no on and off, and Indigo's **All Off** and **All Lights On** can never press your garage door by accident. You work the door with the plugin's own actions, described on the [Actions and triggers](actions-and-triggers.md) page.

## Where the door is

The device list shows one of these:

| Shown as | What it means |
|---|---|
| **Closed** | The bottom sensor sees the door and the top one does not. |
| **Open** | The top sensor sees the door and the bottom one does not. |
| **Moving** | Neither sensor sees the door, so it is somewhere in between. |
| **Stuck** | Neither sensor has seen the door for longer than the travel timeout, 30 seconds to start with. It stays **Stuck** until a sensor sees the door again. |
| **Unknown** | One of the sensors has no reading, or both sensors say the door is at their end, which cannot be true. |

Only **Closed** counts as shut. **Unknown** is never taken as closed, so the alarm, the light and the lamps treat it as a door that may be open.

## What else it shows

These are the names you see when you build a trigger or a control page.

| Shown as | What it means |
|---|---|
| **Door state** | Closed, Open, Moving, Stuck or Unknown, as above. |
| **Direction of travel** | **opening** or **closing** while the door is between its two ends, worked out from the end it was last seen at, and **none** otherwise. A page or trigger that opens mid-trip can use it to say which way the door is going. |
| **Is open** | True only when the door is fully open, not while it is moving or stuck. |
| **Minutes open** | How many whole minutes since the door last left the closed position, and 0 when it is closed. If the plugin restarts while the door is open, the count starts again from the restart. |
| **Alert level** | 0 when all is well, 1 when the door has been left open, and 2 when that has become urgent. The [How it works](how-it-works.md) page explains when each one applies. |
| **Last travel time (s)** | How many seconds the door took on its last trip, from leaving one end to reaching an end. A door that gets slower over the months can be a sign the springs need attention. |
| **Sensors healthy** | False when both sensors say the door is at their end at once, which usually means a sensor or magnet has come loose. |
| **Last opened** | The date and time the door last reached the top, such as `2026-09-27 08:15:04`. |
| **Last closed** | The date and time the door last reached the bottom. |
| **Last operated by** | What last pressed the relay through the plugin. It shows the note you typed into the action, or, if you left the note blank, **action:open**, **action:close**, **action:toggle** or **action:pulse**. It only changes when the relay is really pressed, so not in Shadow Mode. |

Door state also gives you a true-or-false condition for each position, such as whether the door is closed, which makes trigger conditions easy to set up.

## More than one door

Each door needs its own device, with its own two sensors and relay. Every trigger lets you choose one door or any door.

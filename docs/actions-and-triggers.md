---
title: Actions and triggers
nav_order: 6
---

# Actions and triggers

## Working the door

The plugin's actions are listed under **Garage Door** when you add an action to an action group, a schedule, a trigger or a control page button. Each one asks you to pick the door, and has one optional box, a note that shows on the door device as **Last operated by** — such as "Hall button" or "Dashboard", so you can see later what opened it. Click **OK** to save the action, even if you leave the note blank.

| Action | What it does |
|---|---|
| **Open Garage Door** | Presses the relay, unless the door is already open, in which case it writes "already open, nothing to do" to the Event Log and does nothing. |
| **Close Garage Door** | Presses the relay, unless the door is already closed, in which case it does nothing. |
| **Toggle Garage Door** | Presses the relay, whatever the door is doing. This suits a wall button. |
| **Pulse Relay (diagnostic)** | Presses the relay, whatever the door is doing, for testing. It ignores the note and always shows **action:pulse**. |
| **Re-read Door State** | Reads both sensors again and writes where the door is to the Event Log. It does not press the relay, and it ignores the note. |

The opener decides which way the door goes, so a press while the door is part-way does whatever your opener does with a press at that point.

Every press follows the same rules:

- **In Shadow Mode nothing is pressed.** The Event Log says the press would have happened, and how to turn Shadow Mode off.
- **A second press within five seconds is ignored,** with a warning in the Event Log, so a double tap on a button does not open the door and then close it again.
- **The relay is switched on for one second, then off.** If anything goes wrong in between, the plugin still tries to switch the relay off, so it is never left on.
- **If no relay is picked** in the door's settings, the Event Log says so and nothing happens.
- After a press, the Event Log says the relay was pulsed and why, and **Last operated by** shows the note.

## Triggers

To use one, create a new trigger, set its type to **Garage Door**, choose the event, and choose a door in **Which door**, or leave it on **- any door -**. Then add whatever you want to happen.

| Trigger | Runs when |
|---|---|
| **Garage Door Opened** | The door reaches the fully open position. |
| **Garage Door Closed** | The door reaches the fully closed position. |
| **Garage Door Started Moving** | The door leaves either end and neither sensor sees it. |
| **Garage Door Left Open** | The plugin raises a level 1 alert — the door has been open for the first alert time — and again at each repeat. |
| **Garage Door Still Open (urgent)** | The plugin raises a level 2, urgent, alert, and again at each repeat. |
| **Garage Door Stuck Part-Way** | The door has been between the two ends for longer than the travel timeout. The alarm goes urgent at the same moment, so **Garage Door Still Open (urgent)** runs too, unless the alarm was urgent already. |
| **Garage Door Sensor Fault** | Both sensors say the door is at their end, which cannot be true. |

The [How it works](how-it-works.md) page explains when each alert is raised and at which level.

These triggers run in Shadow Mode as well, but not when the plugin starts up, because nothing has happened then.

For example, you could have **Garage Door Left Open** send a quiet notification to your phone, and **Garage Door Still Open (urgent)** send one that makes a noise.

## Conditions and control pages

Every trigger, schedule and action group condition can also test the door device's states, such as **Door state** being Closed or **Minutes open** being more than 30. The [Your garage door](devices.md) page lists them all.

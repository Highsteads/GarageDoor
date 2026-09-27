---
title: Settings
nav_order: 7
---

# Settings

The plugin needs no passwords, accounts or keys. Everything it uses is a device or variable already in your Indigo system.

## The plugin's settings

Open these with **Plugins → Garage Door → Configure**. They apply to every door.

| Setting | What it does |
|---|---|
| **Shadow Mode — watch and report, do not operate the door** | Ticked to start with. While it is ticked the plugin never presses the relay, switches the garage light or changes the lamps, as the [Shadow Mode](shadow-mode.md) page explains. A change takes effect as soon as you click **Save**. |
| **Logging level** | Debug, Info or Warning. Info to start with. Debug adds the plugin's working notes to the Event Log, and Warning leaves only warnings and errors there. The plugin's own log file keeps everything whatever you pick. A change takes effect as soon as you click **Save**. |

## Each door's settings

Open these by double-clicking the door device. Each device box lists every device in your Indigo system, whichever plugin it belongs to, with **- none -** at the top for leaving it blank.

### The sensors

| Setting | What it does |
|---|---|
| **Bottom contact (made = door closed)** | The sensor that sees the door when it is fully closed. |
| **Top contact (made = door open)** | The sensor that sees the door when it is fully open. |

Both are needed. Until they are picked, the Event Log says the door is not configured yet, and the door shows **Unknown**.

### The relay

| Setting | What it does |
|---|---|
| **Door relay (momentary)** | The relay that presses your opener's button. Without one the door can be watched but not worked. |
| **Pulse length (ms)** | How long the relay stays on for each press, in thousandths of a second. 1000, one second, to start with. A blank box or 0 means one second, and anything over 10000 is cut to ten seconds, because an opener wants a press, not a held button. |
| **Travel timeout (s) — longer than this and it is stuck** | How many seconds the door may spend between the two ends before it counts as stuck. 30 to start with. Set it a little longer than your door takes to open or close. |
| **Ignore repeat operations within (s)** | How many seconds after one press another is ignored, so a double tap on a button does not stop the door half-way. 5 to start with. 0 lets every press through. |

### The alarm

| Setting | What it does |
|---|---|
| **First alert after (minutes)** | How long the door can be open before the alarm goes to level 1. 15 to start with. |
| **Escalate to urgent after (minutes)** | How long the door can be open before the alarm goes to level 2, urgent. 45 to start with. |
| **Repeat the alert every (minutes, 0 = once)** | How often the alert is repeated while the door stays open. 15 to start with. At 0 it is only repeated when it becomes more urgent. |
| **"Away" variable name (blank to ignore)** | The name of an Indigo variable that is **true** when nobody is home. **Away** to start with. The plugin finds it by name, so deleting and recreating the variable does not break anything. |
| **Urgent straight away when nobody is home** | Ticked to start with. While the away variable is true, the alarm is urgent as soon as the door leaves the closed position. |
| **"Dark" variable name (blank to ignore)** | The name of an Indigo variable that is **true** when it is dark. **Nightime** to start with. |
| **Urgent when it is dark** | Ticked to start with. While the dark variable is true, the first alert is urgent rather than level 1. |

A blank or unreadable number in any of these boxes falls back to the figure it starts with, so the alarm always works.

### The garage light

| Setting | What it does |
|---|---|
| **Garage presence sensor (optional)** | A presence or motion sensor in the garage. Only used when **Only light it if somebody is actually in there** is ticked. |
| **Garage light (optional)** | The light to switch. Leave it blank and the plugin leaves your garage light alone. |
| **Light-level sensor (optional)** | A sensor that measures light in lux, used to tell whether it is dark. |
| **Only light it if somebody is actually in there** | Unticked to start with. Ticked, the light only comes on when the presence sensor shows somebody. |
| **Only light it when it is dark** | Ticked to start with. The light only comes on when the light-level sensor reads at or below the figure below. If you have no light-level sensor, the plugin goes by the **"Dark" variable** instead, and if it cannot read that either, the light comes on whenever the door opens. |
| **Dark below (lux)** | The light level at or below which it counts as dark. 30 to start with. A figure such as 12.5 works too. |

The [How it works](how-it-works.md) page explains exactly when the light is switched.

### The lamps in the house

| Setting | What it does |
|---|---|
| **Let the lamps follow the door** | Ticked to start with. Untick it and the plugin leaves both lamps alone. |
| **Signal lamp (colour-capable)** | A colour lamp that shows what the door is doing. |
| **Colour while moving (R,G,B 0-100)** | Three numbers from 0 to 100 for red, green and blue, separated by commas. `0,0,100`, blue, to start with. |
| **Colour while open (R,G,B 0-100)** | `100,0,0`, red, to start with. |
| **Colour when restored on closing (R,G,B 0-100)** | The colour the lamp goes back to when the door closes and the reference lamp is on. `100,100,100` to start with. |
| **White temperature when restored (K)** | The white temperature, in kelvin, the lamp goes back to at the same time. 3000, a warm white, to start with. |
| **Second lamp, on/off only (optional)** | A lamp that comes on while the door is open. |
| **On closing, match this lamp's on/off state** | The reference lamp. When the door closes, both lamps go back on if this lamp is on, and off if it is off. |

If a colour box is blank or cannot be read, the lamp uses the colour it starts with. Leave both lamp boxes blank and none of this happens.

### HomeKit

| Setting | What it does |
|---|---|
| **HomeKit mirror variable name (optional)** | The name of an Indigo variable the plugin sets to on or off as the door closes and opens, for HomeKit to read. The variable must already exist. |
| **Inverted — "on" means CLOSED (HomeKitLink-Siri expects this)** | Ticked to start with, so **on** means closed. Untick it and **on** means open. |

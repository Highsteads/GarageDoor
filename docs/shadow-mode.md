---
title: Shadow Mode
nav_order: 3
---

# Shadow Mode

The plugin arrives with **Shadow Mode** switched on, and I would leave it on for a few days.

## What it does

While Shadow Mode is on, the plugin:

- works out where the door is and shows it on the device,
- runs the open-door alarm and writes it to the Event Log,
- runs your triggers when the door opens, closes, is left open and so on,
- keeps the HomeKit variable up to date, if you have named one.

It does **not**:

- press the door relay — an open, close or toggle action writes a line to the Event Log saying what it would have done, and stops there,
- switch the garage light,
- change the lamps in the house.

A garage door is something you rely on to get the car out in the morning, so it makes sense to watch the plugin follow the real door for a while before it is given the relay.

## What to watch for

- Each time the door opens or closes, the Event Log says it is moving, then open or closed, at the moment it happens.
- On the door device, **Last travel time** — how many seconds the last trip took — looks about right for your door.
- The device never says **Stuck** when the door is not.

## Handing over

When you are happy:

1. Point your action groups, control page buttons and wall-button triggers at the plugin's actions — **Open Garage Door**, **Close Garage Door** and **Toggle Garage Door** — instead of at the relay.
2. Point anything that should follow the door, such as notifications, at the plugin's triggers, and switch off whatever did that job before.
3. Open **Plugins → Garage Door → Configure**, untick **Shadow Mode**, and click **Save**. The Event Log confirms that door control is enabled.

Do step 2 at the same time as step 3, not before. Until then your old set-up is still doing its job, and if both run you get everything twice.

You can tick **Shadow Mode** again at any time, and the plugin goes back to watching only. The change takes effect as soon as you click **Save**, with no restart.

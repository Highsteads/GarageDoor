---
title: Getting started
nav_order: 2
---

# Getting started

This takes about ten minutes, and you only do it once.

## What you need

- Indigo 2025.2 or later.
- **Two contact sensors on the door,** one at each end of its travel. The bottom one should see its magnet when the door is fully closed, and the top one when the door is fully open. Each must have a state called **contact** in Indigo, which is on when the magnet is against the sensor. The **Test Garage Door Setup** menu item tells you if a sensor does not have one.
- **The relay that works your door opener,** already set up as a device in Indigo. The plugin presses it the way you would press the button on the wall — on for a second, then off — and the opener decides whether the door goes up or down.

These are optional, and you can add them later:

- A presence or motion sensor in the garage.
- The garage light, and a light-level sensor to say when it is dark.
- A colour lamp in the house, and a second lamp, to show what the door is doing.
- An Indigo variable that is **true** when nobody is home, and one that is **true** when it is dark. The plugin looks for variables called **Away** and **Nightime** to start with.
- An Indigo variable for HomeKit to read, if you show the door in Apple's Home app.

## 1. Install the plugin

1. Go to the [Releases page](https://github.com/Highsteads/GarageDoor/releases/latest) and download `GarageDoor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `GarageDoor.indigoPlugin`
3. Double-click `GarageDoor.indigoPlugin` — Indigo will install it automatically

Indigo asks whether to enable the plugin. Say yes.

## 2. Leave Shadow Mode on

Open **Plugins → Garage Door → Configure**. **Shadow Mode** is ticked, and it should stay ticked for now. While it is on, the plugin watches the door and tells you what it sees, but never presses the relay or switches a light or lamp, so whatever runs your door today carries on as before. Click **Save**.

The [Shadow Mode](shadow-mode.md) page explains how to hand over when you are ready.

## 3. Add your door

1. In Indigo, choose **New Device**.
2. Set **Type** to **Garage Door**, and the model to **Garage Door**.
3. Pick the sensor at the bottom in **Bottom contact (made = door closed)**, and the one at the top in **Top contact (made = door open)**. If you get them the wrong way round, swap them here rather than anywhere else.
4. Pick the opener's relay in **Door relay (momentary)**.
5. If your variables for "nobody is home" and "it is dark" have other names, type them into **"Away" variable name** and **"Dark" variable name**. Clear a box if you have no such variable.
6. Add the garage light, lamps and HomeKit variable now if you want them, or leave them blank. Every box is explained on the [Settings](settings.md) page.
7. Click **Save**.

## 4. Check it works

Choose **Plugins → Garage Door → Test Garage Door Setup**. The Event Log shows each sensor, relay, lamp and variable you have picked, with **PASS** if the plugin can read it and **FAIL** if it cannot, then where the door is now.

The new device in the device list should show **Closed** or **Open** to match the real door. Open and close the door the way you usually do, and each time the Event Log should have a line saying the door is moving, then open or closed.

If anything does not match, the [When something goes wrong](troubleshooting.md) page goes through the usual causes.

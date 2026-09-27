---
title: Version history
nav_order: 10
---

# Version history

The newest version is at the top.

## 1.7 — 11 September 2026

The plugin carries a note of where its code lives on GitHub, the same way other Indigo plugins do. Nothing else changed.

## 1.6 — 31 August 2026

**Closing the door no longer switches the house lamps off when the reference lamp cannot be read.** When the door closes, the lamps are meant to go back to how the house had them, judged by the reference lamp you pick. In my house that lamp had been taken out of the room in August, and a reference lamp that could not be read was being treated as one that was off, so every close turned both lamps out. Now a reference lamp that cannot be read leaves both lamps exactly as they are, and the Event Log says once each time the plugin starts which device it cannot find. With no reference lamp picked at all, a closed door still switches both lamps off.

## 1.5 — 2 August 2026

Fixes "Action has not been completely configured" on the door actions. Indigo only counts an action as set up once you have clicked OK in its box, and 1.2 had taken the box away, so the actions failed every time they ran. The box is back, with an optional note and nothing you have to fill in.

## 1.4 — 2 August 2026

The garage light follows the door and the light level. **Only light it if somebody is actually in there** is still there, but it is off to start with, because a light that waits until it is sure somebody is in the garage leaves you standing in the dark.

## 1.3 — 2 August 2026

The garage light is checked every second, not only when the door moves, so walking into the garage a minute after opening the door turns the light on.

## 1.2 — 2 August 2026

The door actions are listed under **Garage Door** in the action list, rather than under Indigo's own **Device Actions** next to Turn On, Turn Off and Toggle, where they were easy to confuse with the relay's own.

## 1.1 — 2 August 2026

The plugin can look after the house lamps that show what the door is doing — blue while it moves, red while it is open, and back to matching a reference lamp when it closes. Every part is optional and every colour is a setting. Leave the lamps blank and none of it happens.

## 1.0 — 2 August 2026

First release. The door's position from two sensors, an open-door alarm that becomes urgent when nobody is home or it is dark, seven triggers, open, close and toggle actions, an optional garage light and a HomeKit variable. It starts in Shadow Mode.

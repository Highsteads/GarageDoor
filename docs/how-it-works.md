---
title: How it works
nav_order: 5
---

# How it works

You do not need to know all of this to use the plugin, but it explains why the door, the alarm and the lights behave as they do.

## Where the door is

The two contact sensors are **position sensors**. Each one only says whether the door is at its own end of the travel — the bottom one when the door is shut, the top one when it is fully open. Neither can tell you on its own whether the door is open, so the plugin reads both together:

- bottom sees the door, top does not — **Closed**
- top sees the door, bottom does not — **Open**
- neither sees the door — **Moving**, and **Stuck** once that has gone on longer than the travel timeout
- both see the door — **Unknown**, because that cannot happen, and the plugin logs a warning and runs your **Garage Door Sensor Fault** triggers
- either sensor has no reading at all — **Unknown**
- either sensor is switched off in Indigo, marked as in error by its plugin, or reported offline — **Unknown**, with **Sensors healthy** false and **Sensor problem** naming the sensor, and the plugin logs a warning and runs your **Garage Door Sensor Fault** triggers

A sensor that has never reported is not taken as either answer. Nor is a sensor its plugin has lost: Zigbee2MQTT Bridge, for one, marks a sensor offline and leaves its last reading in place, so a garage that went off the network used to stay **Closed**. The door is only called closed or open when both sensors have said so and both are working.

The plugin hears straight away when either sensor changes, and it also checks every door once a second, which is how it notices a door that has been moving too long or open too long.

## The open-door alarm

The alarm starts counting when the door leaves the closed position, and stops the moment it is closed again. It has three levels:

| Level | When |
|---|---|
| **0** — all is well | The door is closed, or it has been open for less than the first alert time and none of the urgent cases below applies. |
| **1** — left open | The door has been open for the first alert time, 15 minutes to start with. |
| **2** — urgent | Any one of these: the door is stuck, nobody is home, the door has been open for the escalation time (45 minutes to start with), or it has reached the first alert time and it is dark. |

"Nobody is home" and "it is dark" come from two Indigo variables you name in the door's settings. The plugin reads each one by name and treats it as true only when its value is the word **true**. If nobody is home, the alarm goes straight to urgent as soon as the door leaves the closed position. You can switch off either of these in the door's settings.

Each time it raises an alert, the plugin writes a warning to the Event Log, such as "Garage door is open (for 15 minutes)", with "Nobody is home." or "It is dark." added when they apply. It also runs your **Garage Door Left Open** triggers at level 1, or your **Garage Door Still Open (urgent)** triggers at level 2. It raises an alert:

- as soon as the door reaches level 1 or level 2,
- again if it goes up from level 1 to level 2,
- and again every repeat interval, 15 minutes to start with, for as long as the door stays open. Set the repeat to 0 and there are no repeats.

If the plugin restarts while the door is open, it carries on counting from when the door was really opened, and does not send an alert again that it had already sent. It goes by the time it saved before stopping, as long as it stopped less than half an hour earlier. Otherwise it goes by when the bottom sensor last changed, which can only make the count shorter, never longer.

The plugin does not send notifications itself. Hang a Pushover message, an email or anything else you like off those two triggers.

The alarm runs in Shadow Mode too.

## The garage light

If you pick a garage light in the door's settings, the plugin switches it, unless Shadow Mode is on:

- **off** the moment the door closes,
- **on** when the door is not closed and it is dark enough, which means the light-level sensor reads at or below the **Dark below (lux)** figure, 30 to start with.

If you tick **Only light it if somebody is actually in there**, the presence sensor must also show somebody, and the light goes off when it shows nobody. That is off to start with, because a presence sensor can be slow to notice someone, and a garage light that waits leaves you standing in the dark.

If you have no light-level sensor, the plugin judges "dark" by the variable you named in **"Dark" variable name**: the light comes on when it is **true** and stays off when it is **false**. If there is no such variable, the light comes on whenever the door opens, and if you named one the plugin cannot find, the Event Log says so once each time the plugin starts.

If you have picked a light-level sensor or a presence sensor and it has stopped giving a reading, the plugin leaves the light as it is rather than guess.

The plugin checks the light every second, but only sends a command when its answer changes, so if you switch the light by hand it stays as you left it until the door or the light level changes the answer.

## The lamps in the house

This is optional. I use it so anyone in the house can see what the garage door is doing without looking. If you pick a colour lamp, and a second lamp if you like, the plugin sets them each time the door changes, unless Shadow Mode is on:

| The door is | The colour lamp | The second lamp |
|---|---|---|
| Moving, stuck or unknown | The moving colour, blue to start with | Left as it is |
| Open | The open colour, red to start with | On |
| Closed | Matches the reference lamp — see below | Matches the reference lamp |

Each time the colour lamp is given a colour, it is also set to full brightness.

When you untick **Shadow Mode**, the plugin sets the lamps to suit the door as it is, without waiting for the door to move. A lamp that is already showing the right thing is left alone. It does this once, so if you change a lamp by hand afterwards the plugin does not change it back.

When the door closes, the lamps go back to how the house had them, judged by a **reference lamp** you pick — a lamp elsewhere in the house that is on in the evening and off during the day, say:

- If the reference lamp is on, the colour lamp goes to the restore colour and white temperature, and the second lamp comes on.
- If the reference lamp is off, or you have not picked one, both lamps go off.
- If you have picked a reference lamp and the plugin cannot read it — it has been deleted, for example — both lamps are left exactly as they are, and the Event Log says once, each time the plugin starts, which device it cannot find, so you can pick another or clear the box.

## The HomeKit variable

If you name an Indigo variable for HomeKit, the plugin sets it to **on** or **off** each time the door reaches closed or open. With **Inverted** ticked, which it is to start with, **on** means closed, which is what the HomeKitLink-Siri plugin expects for a garage door. Untick it and **on** means open.

While the door is moving, stuck or unknown the variable is left as it was, so it never says the door is shut when the plugin is not sure.

The variable has to exist already. The plugin does not create it.

## When the plugin starts

When the plugin starts, it reads both sensors and sets the door's state without running any triggers, because nothing has actually happened. It does set the HomeKit variable to match the door, and, unless Shadow Mode is on, the lamps and the garage light too.

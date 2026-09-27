---
title: When something goes wrong
nav_order: 9
---

# When something goes wrong

Each section starts with what you see, then what it means and what to do. **Plugins → Garage Door → Test Garage Door Setup** is the best first step for most of them.

## The door shows "Unknown"

The plugin cannot tell where the door is.

- If the Event Log says the door is **not configured yet**, open the door device and pick both contact sensors.
- If **Test Garage Door Setup** says **FAIL** for a sensor, it either no longer exists or has no **contact** state. Pick the right device, or a sensor that has one.
- If **Sensors healthy** is false, both sensors say the door is at their end at once. Check that each magnet is still in line with its sensor, and that you have not picked the same sensor twice.
- If one sensor has simply not reported yet, open and close the door once.

## The door shows "Open" when it is shut, or the other way round

The two sensors are the wrong way round. Open the door device and swap them over in **Bottom contact** and **Top contact**.

## The door shows "Stuck" when it is not

The door took longer than the travel timeout to get from one end to the other. Look at **Last travel time** on the device, and set **Travel timeout** in the door's settings a few seconds longer than that. If the door really did stop, the state clears as soon as a sensor sees it again.

## Nothing happens when I open or close the door from Indigo

- If the Event Log has a line marked `[shadow]` saying the plugin would have pulsed the relay, Shadow Mode is on. The [Shadow Mode](shadow-mode.md) page explains when and how to turn it off.
- If it says **ignoring a repeat operation**, two presses came closer together than **Ignore repeat operations within (s)**, five seconds to start with, and the second was ignored on purpose.
- If it says **already open, nothing to do** or **already closed, nothing to do**, the plugin believes the door is already there. Check the door device shows the right position.
- If it says **no relay configured**, pick the relay in the door's settings.
- If it says **relay pulse failed**, the relay device could not be switched. Check the relay works from Indigo on its own.

## The garage light does not come on

- Check you have picked a **Garage light** in the door's settings, and that Shadow Mode is off.
- If **Only light it when it is dark** is ticked and you have a **Light-level sensor**, it must read at or below **Dark below (lux)**. If the sensor has stopped giving a reading, the plugin leaves the light alone.
- With no light-level sensor, the plugin goes by the **"Dark" variable**, so the light stays off while that variable is **false**.
- If **Only light it if somebody is actually in there** is ticked, the presence sensor must show somebody. Try unticking it.

## The lamps in the house stay as they were when the door closes

If the Event Log says the restore reference **cannot be read**, the lamp picked in **On closing, match this lamp's on/off state** has gone — deleted, or never reports. Pick another lamp, or set the box to **- none -**, in which case both lamps go off when the door closes.

## The alarm goes urgent as soon as I open the door

Your away variable is **true**, and **Urgent straight away when nobody is home** is ticked, so the plugin treats the open door as a door opened in an empty house. Check the variable named in **"Away" variable name** is false when you are at home, or untick the setting.

## The alarm never goes urgent after dark

Check the variable named in **"Dark" variable name** exists and holds the word **true** after dark. **Test Garage Door Setup** shows its name and value, or **FAIL** if no variable has that name.

## The HomeKit variable does not change

- Check the variable named in **HomeKit mirror variable name** exists — the plugin does not create it. If the Event Log says **Could not update the HomeKit variable**, it could not find it.
- The variable only changes when the door reaches fully open or fully closed.
- If HomeKit shows open when the door is shut, change the **Inverted** tick box.

## Still stuck?

Choose **Plugins → Garage Door → Test Garage Door Setup**, copy the lines it writes to the Event Log, and post them on the [Indigo forum](https://forums.indigodomo.com) with a description of what you see. You can also [raise an issue on GitHub](https://github.com/Highsteads/GarageDoor/issues).

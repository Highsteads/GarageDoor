# Garage Door for Indigo

**One Indigo device that knows where your garage door is, and tells you when it has been left open.**

**Version:** 1.9 | **Author:** CliveS & Claude | **Needs:** Indigo 2025.2 or later

**[Read the full guide](https://highsteads.github.io/GarageDoor/)** — setting up, what everything means, and what to do when something goes wrong.

---

## What it does

This plugin gives [Indigo](https://www.indigodomo.com) one device for your garage door. It uses the contact sensors and relay you already have in Indigo, so there is no account, no internet service and nothing else to install.

- **Knows where the door is** — closed, open, moving, stuck part-way or unknown — from a contact sensor at each end of its travel. Anything else in Indigo that wants to know can ask this one device.
- **Raises the alarm when the door is left open,** after 15 minutes to start with, and marks it urgent when nobody is home, when it is dark, when the door is stuck or when it has been open for 45 minutes. It repeats until the door is shut.
- **Runs your triggers** when the door opens, closes, starts moving, is left open, is still open, is stuck, or its sensors disagree, so you choose what happens — a notification, a light, anything else.
- **Opens, closes and toggles the door** from actions, control pages, schedules and triggers, by pressing the opener's relay for one second. A second press within five seconds is ignored.
- **Switches the garage light** on when the door opens and it is dark, and off when it closes.
- **Colours a lamp in the house** blue while the door moves and red while it is open, and puts it back as the house had it when the door closes.
- **Keeps a variable up to date for HomeKit,** with on meaning closed to start with, as the HomeKitLink-Siri plugin expects.
- **Starts in Shadow Mode,** watching and reporting but never pressing the relay or switching a light, until you are ready to hand it the controls.

I wrote it because six different scripts and pages in my Indigo system each worked out for themselves whether the garage was open, and they did not all agree on how.

## What it works with

| You need | For |
|---|---|
| **Two contact sensors** on the door, one at the bottom of its travel and one at the top, each with a **contact** state in Indigo | Knowing where the door is |
| **The relay that works your opener,** as an Indigo device | Opening and closing the door |
| A presence sensor, the garage light and a light-level sensor (optional) | The garage light |
| A colour lamp, a second lamp and a reference lamp (optional) | Showing the door in the house |
| Indigo variables that are true when nobody is home and when it is dark (optional) | Making the alarm urgent |

## Installing

1. Go to the [Releases page](https://github.com/Highsteads/GarageDoor/releases/latest) and download `GarageDoor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `GarageDoor.indigoPlugin`
3. Double-click `GarageDoor.indigoPlugin` — Indigo will install it automatically

## Setting it up

1. Leave **Shadow Mode** ticked in **Plugins → Garage Door → Configure** for the first few days, so your present set-up keeps working the door while you watch the plugin follow it.
2. Create a **New Device**, choose **Garage Door**, and pick the bottom and top contact sensors and the door relay. Add the alarm variables, light, lamps and HomeKit variable if you want them.
3. Choose **Plugins → Garage Door → Test Garage Door Setup**, and check nothing in the Event Log says **FAIL**.
4. Open and close the door, and check the device follows it. When you are happy, point your buttons and notifications at the plugin and untick **Shadow Mode**.

The [full guide](https://highsteads.github.io/GarageDoor/) goes through each step, explains every setting, and covers what to do if something does not work.

## What's new

**v1.9** — The door now says which way it is travelling. A new Direction of travel state reads opening or closing while the door is between its two ends, worked out from the end it was last seen at, and the Event Log says "opening" or "closing" instead of "moving". A page opened part-way through a trip can show the right word at once.

**v1.8** — Pulse length, the repeat-press window and the logging level now do what they say, and the garage light comes on without a light-level sensor, going by your "Dark" variable instead. Test Garage Door Setup now checks the lamps too.

**v1.7** — The plugin carries a note of where its code lives on GitHub, the same way other Indigo plugins do. Nothing else changed.

Every version is listed in the [version history](https://highsteads.github.io/GarageDoor/changelog.html).

## Authors & licence

Vibed into existence by **CliveS**, who knew what he wanted, argued until he got it, and tested it on a real house. Typed at inhuman speed by **Claude** (Anthropic), who mostly did as it was told.

© 2026 CliveS · [MIT licence](LICENSE) — copy it, fork it, bend it, break it, fix it, ship it. If it breaks, you get to keep both pieces.

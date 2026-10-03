---
title: Home
nav_order: 1
---

# Garage Door for Indigo

This plugin gives [Indigo](https://www.indigodomo.com) one device for your garage door, which knows where the door really is — closed, open, moving, stuck part-way, or unknown — how long it has been open, and when it has been left that way long enough to tell you. Everything it needs is already in your Indigo system: two contact sensors on the door, the relay that works the opener, and, if you want them, a few other devices and variables. There is no account, no internet service and nothing else to install.

I wrote it because six different scripts and pages in my Indigo system each worked out for themselves whether the garage was open, and they did not all do it the same way. Now they all ask this one device.

## What it does for you

- **Knows where the door is,** from a contact sensor at each end of its travel. When neither sensor sees the door, it is moving, and if that goes on longer than it should, the door is stuck.
- **Raises the alarm when the door is left open,** marks it urgent when nobody is home, when it is dark or when the door is stuck, and repeats it until the door is shut.
- **Runs your triggers** when the door opens, closes, starts opening or closing, is left open, is still open, is stuck, or its sensors disagree with each other. What happens then is up to you.
- **Opens, closes and toggles the door** from actions, control pages, schedules and triggers, by pressing the opener's relay for you.
- **Switches the garage light** on when the door opens and it is dark, and off when it closes, if you give it a light.
- **Colours a lamp in the house** blue while the door moves and red while it is open, if you give it a colour lamp.
- **Keeps a variable up to date for HomeKit,** if you use one to show the door in Apple's Home app.
- **Starts in Shadow Mode,** watching and reporting but never pressing the relay, until you are happy to hand it the controls.

## Where to go next

| If you want to... | Read |
|---|---|
| Install the plugin and set up your door | [Getting started](getting-started.md) |
| Know why it starts in Shadow Mode, and how to hand over | [Shadow Mode](shadow-mode.md) |
| Know what the door device shows in Indigo | [Your garage door](devices.md) |
| Understand the alarm, the light and the lamps | [How it works](how-it-works.md) |
| Work the door, or react to it, from triggers and schedules | [Actions and triggers](actions-and-triggers.md) |
| Know what every setting does | [Settings](settings.md) |
| Know what each item in the Plugins menu does | [The plugin menu](plugin-menu.md) |
| Sort out a problem | [When something goes wrong](troubleshooting.md) |
| See what changed in each version | [Version history](changelog.md) |

## Download

The latest version is always on the [Releases page](https://github.com/Highsteads/GarageDoor/releases/latest).

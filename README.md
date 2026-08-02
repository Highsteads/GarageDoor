# Garage Door

One Indigo device that owns your garage door — where it actually is, how long it has been open,
the alarm when it has been left that way, and the light that follows whoever walked in.

## Why

A garage door with two contact sensors is deceptively awkward. Neither sensor answers "is it
open" on its own — each only reports whether the door has reached *that* end of its travel — so
every script, page and notification that wants to know ends up carrying its own copy of the
truth table. In this house six of them did, and they did not agree on how: some read the sensor's
`contact` state, one read `onState`, and those two are exact opposites. Both were correct, which
is worse than one being wrong, because a single well-meant tidy-up would have broken half of them
without a sound.

There is a second problem that scripts cannot solve at all. A script runs when something fires
it, so nothing is watching the clock, and a timer expiring needs a listener. An open alarm built
that way sat dead here for three months without anyone noticing. A plugin has a thread that keeps
running, which is the whole difference.

## What it gives you

**One device**, with a proper state — closed, open, moving, stuck or unknown. Mid-travel is
directly observable, because both reeds are apart, so "moving" is measured rather than assumed.
Everything else in your system can ask this one device instead of doing the sums again.

**An alarm that knows the difference between situations.** A door open in daylight with somebody
home is an oversight and can wait fifteen minutes. The same door with the house empty is a
different event and goes out at once. So does one stuck part-way, or open after dark, or open for
the best part of an hour. All four thresholds are yours to set.

**Events rather than opinions.** The plugin tells you the door opened, closed, started moving,
has been left open, is still open, is stuck, or that its sensors are contradicting each other.
What happens next is up to you — point your own action groups at those triggers and keep whatever
notification and lighting behaviour you already have.

**The garage light, if you want it.** On when the door opens and it is dark enough to want it, off the moment the door closes. There is an option to require presence as well, off by default.

**A HomeKit mirror variable**, with an invert option, because HomeKitLink-Siri maps ON to Closed
and that catches everybody once.

## Shadow Mode — read this before anything else

**The plugin ships read-only.** It watches the door, reports its state, fires events and runs the
alarm, but it will not touch the relay or the light. Your existing setup keeps operating the
door.

That is deliberate. A garage door is load-bearing — you want the car out in the morning — and a
new state machine deserves a few days of being watched before it is handed the controls. Leave
Shadow Mode on, watch the log follow the real door, check that `travelSeconds` looks sensible and
that nothing reports "stuck" when it is not, and then turn it off in the plugin's configuration.

One ordering note. While Shadow Mode is on, whatever you have now is still driving your lights,
so do not point your action groups at the new events until you switch over, or you will get both.

## Setting it up

1. Create a **Garage Door** device.
2. Pick the **bottom** and **top** contact sensors. Bottom made means closed, top made means
   open. If yours are the other way round, swap them here rather than anywhere else.
3. Pick the **relay** that operates the door, and set the pulse length. Direction is decided by
   the opener itself — the plugin only ever sends a pulse.
4. Set the alarm thresholds, and name your "away" and "dark" variables if you have them. Both are
   looked up by name, so recreating a variable will not break anything.
5. Optionally add the presence sensor, garage light and light-level sensor.
6. Run **Plugins → Garage Door → Test Garage Door Setup**. It checks every device and variable you
   have named and prints a PASS or FAIL for each, along with the current door state.

## Requirements

Indigo 2025.2 or later. No external services, no credentials, nothing to install — every input is
a device or variable you already have.

## Version history

**1.5** (02-Aug-2026) — Fixes "Action has not been completely configured" on the door actions. Indigo marks an action step as configured when its dialog is completed, and 1.2 had removed the dialog altogether — so the step could never become configured and failed every time it ran. The dialog is back. It asks for nothing you need to fill in.

**1.4** (02-Aug-2026) — The garage light follows the door and the light level by default. Presence-gating is still there as an option but it is now off: a light that waits until it is certain somebody is in the garage leaves you standing in the dark, which is not what a garage light is for.

**1.3** (02-Aug-2026) — The garage light now follows presence properly. It was only being considered when the door itself changed, so walking into the garage a minute after opening it never turned anything on. It is now checked continuously, and only actually switched when the answer changes.

**1.2** (02-Aug-2026) — The door actions now appear under the plugin's own name in the action picker rather than inside Indigo's built-in **Device Actions** submenu, where they sat next to Turn On, Turn Off and Toggle and were easy to confuse with the relay's own. They also no longer ask for anything, so there is no dialog to leave half-finished.

**1.1** (02-Aug-2026) — Takes over the house lamps that announce the door, so the scripts that used to do it can retire. Blue while it moves, red while it is open, and on closing they go back to matching a reference lamp elsewhere in the house. Every part is optional and every colour is a setting — leave the devices blank and none of it happens.

**1.0** (02-Aug-2026) — First release. Door state from two position sensors, escalating
presence-aware open alarm, seven events, open/close/toggle actions, optional garage light and
HomeKit mirror. Ships in Shadow Mode.

## Authors & licence

Vibed into existence by **CliveS**, who knew what he wanted, argued until he got it, and tested it on a real house. Typed at inhuman speed by **Claude** (Anthropic), who mostly did as it was told.

© 2026 CliveS · [MIT licence](LICENSE) — copy it, fork it, bend it, break it, fix it, ship it. If it breaks, you get to keep both pieces.

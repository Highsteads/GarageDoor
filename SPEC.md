# GarageDoor — plugin specification

Agreed 02-Aug-2026. Nothing gets built until this is signed off.

---

## 1. Purpose and success

One plugin owns the garage door: its true state, its operation, and the alarm when
it is left open.

**Why now.** Six places independently re-derive "is the garage open" from the two
raw contact ids — `Garage_Door_Controller.py`, `Morning_Brief.py`,
`Departure_Check.py`, `PushoverNightime.py`, the Dashboards `actionWatch` rules and
its room-door tile. They also disagree on convention: `PushoverNightime` reads
`onState`, the other three read `states.contact`, and **the two are exact
inverses**. Both are correct today. One careless "let's make these consistent" edit
breaks half of them, silently. That is the same shape as the five hand-rolled
timezone conversions in SigenEnergyManager, two of which were quietly wrong for
weeks.

**Success criterion.** Every consumer asks one device one question and gets one
answer, and the door tells you itself when it has been left open.

Second prize, but real: **nothing is long-running today**, which is why the
15-minute open alarm sat dead from May to August. A script runs when something
fires it; a timer expiring needs a listener. `runConcurrentThread` is the fix, and
it removes the timer device and its trigger entirely.

---

## 2. Scope

**In**
1. Door state and the escalating open alarm (core).
2. Presence- and time-aware alert thresholds.
3. The garage lights, gated on presence and lux.
4. Custom events so the hall/conservatory lamp signalling keeps working.

**Out of v1.0**
- **Auto-close on absence.** Decided against. A radar occupancy sensor can lose a
  motionless person — proven by the Bedroom 1 FP300s — and the failure mode is a
  door closing on somebody. The plugin alerts; the Dashboards hub offers a one-tap
  close, which since v2.75.0 confirms the door actually moved.
- Hall/conservatory lamp colour logic (events instead — see §6).
- Direct Pushover sending (events instead — see §6).
- Multiple doors. One device, one door. The design does not preclude a second.

**No external system.** No transport, no auth, no rate limits, no wire format to
guess. Every input is a local Indigo device read through `subscribeToChanges`. The
usual riskiest part of a new plugin does not apply here.

---

## 3. Device model

**Type: `custom`.** Two reasons, one of them safety.

- A `relay`-typed door is **sweepable**. "All devices off" or "all lights on" would
  operate the garage door. That is a real way to open your garage by accident.
- On `custom` devices the reserved-name traps do not apply, so `doorState` can be a
  proper enum without fighting `onOffState`.

The cost is no native on/off row in the Indigo UI. Accepted — the door is operated
by actions, not by a switch.

### States

| State | Type | Notes |
|---|---|---|
| `doorState` | List enum | `closed` / `open` / `moving` / `stuck` / `unknown`. **Display state.** An enum auto-generates `doorState.closed` etc. as bool sub-states, which makes trigger conditions trivial |
| `isOpen` | Boolean | Convenience for consumers that just want the one bit |
| `openDurationMinutes` | Integer | 0 when closed |
| `alertLevel` | Integer | 0 quiet, 1 left-open, 2 urgent |
| `lastOpened` / `lastClosed` | String | Local timestamps |
| `lastOperatedBy` | String | `hall-button` / `homekit` / `dashboard` / `plugin` / `manual` |
| `travelSeconds` | Integer | Last measured travel. A door getting slower is a spring beginning to fail — worth having before it strands the car |
| `sensorsHealthy` | Boolean | False when both reeds read made, which is physically impossible |

`UiDisplayStateId` = `doorState`. **Fixed at creation and read-only afterwards** —
getting it wrong means delete and recreate, so it goes in the scaffold correctly
first time.

### Deriving the state

Mirrors `Garage_Door_Controller.py:120-128`, using `states.contact` only:

```
bottom.contact and not top.contact  -> closed
top.contact and not bottom.contact  -> open
neither made                        -> moving, or stuck past the travel timeout
both made                           -> sensor fault (impossible in the real world)
```

**Never `onState` on these two.** They are position sensors: `top.onState == true`
means the door is *not* at the top. An absent or unreadable contact is **unknown**,
never a match — `None == False` is True in Python, so a silent sensor would
otherwise read as a confirmed reading. See `feedback_absent_state_is_never_a_match`.

---

## 4. Threading

`runConcurrentThread` on a 1-second tick — enough resolution for travel timing and
the alarm clock, cheap enough to ignore. Contact edges arrive by
`subscribeToChanges`, not polling.

No worker threads, no queues, no asyncio. Nothing here justifies them.

**The plugin must never make an HTTP request to IWS** — that deadlocks, and
presents as a server-wide outage.

---

## 5. The six architecture questions

1. **State ownership.** The plugin device is the single owner of door state. The
   `garage_door_state` variable becomes a **derived mirror**, written by the plugin
   and never read back for a decision. The contacts are inputs and are never
   duplicated as authoritative. No fact lives in two places.
2. **Failure isolation.** The whole per-tick body is wrapped, not a fraction of it.
   A lamp or light failure must never stop the alarm — that is the one job that
   matters. Every event fire is individually guarded.
3. **Config-blank safety.** Every `int()`/`float()` is coerced *and* guarded. A
   never-configured install starts, logs one INFO line saying it is awaiting
   configuration — **INFO, not ERROR; awaiting config is not a fault** — and does
   nothing.
4. **Idempotency and loops.** `deviceUpdated` carries the `pluginId` loop guard.
   Open and close are idempotent: already open means no pulse. Re-asserting the
   same state never fires the relay. The alarm re-arms from elapsed time, not from
   a counter that something else could re-trigger.
5. **Termination.** The alarm escalates to a cap and then repeats on a fixed
   interval — it does not accelerate without bound. Travel is bounded by the
   timeout, after which the state is `stuck` and stays there until a contact moves.
6. **Test seam.** Two pure functions, no Indigo import:
   `derive_state(bottom_contact, top_contact, elapsed)` and
   `alarm_decision(state, open_minutes, away, night, cfg)`. Everything interesting
   is decided in those two, so the contract tests drive real logic rather than a
   copy of it.

---

## 6. Events and actions

### Events (`Events.xml`)

The plugin says *what happened*; you decide what to do about it. This is what keeps
it shareable while your exact lamp behaviour — including the Gold Lamp restore
logic — stays yours, in the action groups that already implement it.

| Event | Fires when |
|---|---|
| `doorOpened` | Reached the top |
| `doorClosed` | Reached the bottom |
| `doorStartedMoving` | Left a known position |
| `doorLeftOpen` | First alarm threshold |
| `doorStillOpen` | Escalation threshold |
| `doorStuck` | Mid-travel past the travel timeout |
| `sensorFault` | Both reeds made, or a contact silent too long |

Alerting rides these: `doorLeftOpen` and `doorStillOpen`, plus `alertLevel` and
`openDurationMinutes` on the device for any condition you want to build. No
notification vendor is baked in.

### Actions (`Actions.xml`)

`openDoor`, `closeDoor` (both idempotent), `toggleDoor` (what the Hall button
uses), `pulseRelay` (raw, diagnostics), `refreshState`.

`uiPath` values are PascalCase with no spaces — a space crashes the Indigo client.

---

## 7. Configuration

Every id below is a device or variable picker, never a literal. This is what makes
it installable by someone who is not Clive.

- Bottom contact, top contact
- Relay device(s) + pulse milliseconds + travel timeout (default 30 s) + operation
  debounce (default 5 s)
- Alarm: first threshold **15 min**, escalate **45 min**, "urgent immediately when
  away", "urgent when dark"
- `Away` variable, `Nightime` variable — resolved **by name with an id fallback**,
  because a variable that is deleted and recreated keeps its name but not its id
- Presence sensor
- Garage light, lux sensor, lux threshold, "only if dark", "only if someone is there"
- HomeKit mirror variable + an **invert** toggle (`garage_door_state` is inverted
  here: `"on"` = closed)
- **Shadow mode** (see §8)

No secrets. Nothing goes in `IndigoSecrets.py` — there is no external system.

---

## 8. Cutover — shadow mode first

The door is load-bearing. v1.0 ships **read-only**:

- Tracks state, fires events, runs the alarm, writes its own states.
- **Does not touch the relay.** Actions log what they *would* do.
- The existing scripts keep operating the door throughout.

Verify against the real door for a few days — every event in the log at the moment
it should be, `travelSeconds` sensible, no spurious `stuck`. Then v1.1 flips
`shadowMode` to False and takes control.

**Do not wire the lamp action groups to the new events until cutover** — during
shadow the old contact triggers are still firing them, and you would get both.

### Cutover checklist (v1.1)

- Repoint action groups `1463818396` / `780532115` at the plugin actions
- Repoint the Hall button trigger `805629096` at `toggleDoor`
- Disable contact triggers `786950680`, `1238049936`, `269733411`, `1734054076`;
  hang the lamp action groups off the plugin events instead
- Disable trigger `1133886685`, retire timer device `1197322462`
- Retire `Garage_Door_Controller.py` and its five entry points, plus
  `Garage_Door_Open_Alarm.py`
- Point the four consumers at the plugin device: `Morning_Brief.py`,
  `Departure_Check.py`, `PushoverNightime.py`, and Dashboards (its `actionWatch`
  rules collapse to one condition on `doorState`)

That last line is the whole point of the exercise.

---

## 9. Tests

Contract tests from day one, `tests/run.sh` as the gate, following the Dashboards
pattern.

- **Device zoo** — synthetic contact shapes through `derive_state`: closed, open,
  mid-travel, both-made fault, one sensor silent, both silent, string `"True"`/
  `"False"` values, travel timeout boundary.
- **Alarm matrix** — `alarm_decision` across away/home × dark/light × stuck ×
  duration, including the boundaries at 15 and 45 minutes.
- **Absent state is never a match** — an unreported contact must never produce
  `closed` or `open`. This has bitten twice already.
- **Idempotency** — open on an open door pulses nothing.
- **Shadow mode** — no relay command escapes while it is on. Worth a test of its
  own, because it is the only thing standing between a bug and a moving door.

---

## 10. Repo and release

- `Highsteads/GarageDoor`, bundle `com.clives.indigoplugin.garagedoor`
- Bundle at repo root, README at repo root only, MIT with the standard footer
- Topics: `indigo`, `indigo-domotics`, `home-automation`, `indigo-plugin`,
  `garage-door`, `zigbee`. Issues enabled.
- `PluginVersion 1.0`, `CFBundleVersion 1.0.0`, `ServerApiVersion 3.0`
- GitHub release at v1.0 — but only after shadow mode has proven itself

---

## Sign-off

Confirm or amend. Nothing is built until then.

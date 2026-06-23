# Timing And Train Types

## Time Unit

The simulator uses a fixed clock:

```text
1 tick = 30 simulated seconds
```

Tick counts remain useful for deterministic tests, while metrics also expose
seconds through `total_time_seconds`, `waiting_seconds`, and
`completion_time_seconds`.

## Current Train Profiles

This milestone uses uniform adjacent blocks rather than real station distances.
Running time therefore depends only on train type:

| Type | Adjacent-block running time | Scheduled-stop dwell | Stopping behavior |
| --- | ---: | ---: | --- |
| `SLOW` | 2 ticks / 60 seconds | 1 tick / 30 seconds | Stops at every station |
| `FAST` | 2 ticks / 60 seconds | 1 tick / 30 seconds | Stops only at configured stations |
| `EXPRESS` | 1 tick / 30 seconds | 1 tick / 30 seconds | Stops only at configured stations |

Slow and fast services have equal running speed. Fast services complete the route
sooner only because they skip selected station dwells. Express services both skip
more stations and traverse each block faster.

`scheduled_stops` stores station indexes for FAST and EXPRESS services. The
destination is always treated as a stop. SLOW ignores this tuple and stops at
every intermediate station.

## Movement Lifecycle

A departure no longer moves a train instantly to the next station:

1. The train releases its source station line.
2. It reserves the directional block and destination station line.
3. It remains `IN_TRANSIT` for its profile's running ticks.
4. The block and arrival line remain reserved throughout travel.
5. At arrival, the block reservation is released by rebuilding occupancy.
6. A scheduled stop produces a `DWELL` action before the next departure.

An arrival-line reservation prevents another train from occupying that line, and
prevents a train in a loop from exiting onto it, while a train is approaching.

## Default Scenario

- `UP_EXP1`: EXPRESS from Virar to Dadar; scheduled at Borivali and Dadar.
- `UP_SLOW1`: SLOW from Bhayandar to Dadar; stops everywhere.
- `DOWN_FAST1`: FAST from Dadar to Virar; scheduled at Andheri, Borivali, and Virar.

The express initially waits behind the slow train, catches it at Borivali because
of the shorter block time, and uses the existing priority-loop rule to overtake.
The DOWN fast local independently demonstrates skipped and scheduled stops.

## Deliberate Limits

- Every adjacent block is currently treated as equal length.
- There are no kilometre distances, speed limits, acceleration, or braking curves.
- Loop entry and exit consume an action opportunity but have no separate running
  duration.
- Overtaking is still triggered by immediate occupancy and priority; evaluated
  overtaking plans remain future work.
- Station-to-station track is one block rather than multiple automatic-signalling
  sections.

Real distances and per-block running times can later replace the profile defaults
without changing UP/DOWN occupancy or stop-pattern behavior.

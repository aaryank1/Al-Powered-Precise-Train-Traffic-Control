# UP, DOWN, Main, and Loop Lines

## The Short Explanation

`UP` and `DOWN` identify the two designated railway directions. They do not mean
uphill/downhill, north/south, or a track drawn above/below another track.

Indian railway usage generally treats a movement **toward the controlling railway
headquarters or principal terminal as UP**, and a movement away from it as DOWN.
The designation is operational, however, so the working timetable and station
working rules for the particular route are authoritative.

For this project's Western Railway section, Churchgate is the city-side reference:

```text
UP:    Virar -> Bhayandar -> Borivali -> Andheri -> Bandra -> Dadar -> Churchgate
DOWN:  Churchgate -> Dadar -> Bandra -> Andheri -> Borivali -> Bhayandar -> Virar
```

The code stores stations from Virar to Dadar. It therefore declares increasing
station indexes as `UP` and decreasing indexes as `DOWN`.

## Why There Are Two Main Lines

The old model represented a **single-line railway**. Both directions shared the
same physical block, so opposing trains needed a loop station in order to cross.

A normal **double-line railway** has two continuous running tracks:

- `UP_MAIN` normally carries UP trains.
- `DOWN_MAIN` normally carries DOWN trains.

This allows trains in opposite directions to pass each other at the same location
without conflict because they occupy different physical tracks. They still need
safe spacing from trains following them on the same directional track.

In code, the parallel blocks between Borivali and Andheri are distinct resources:

```text
(Borivali, Andheri, UP)     !=     (Borivali, Andheri, DOWN)
```

The model does not yet support temporary wrong-line working, where an authorized
train uses the line normally assigned to the opposite direction.

## Why There Can Be Two Loop Lines

A loop is a local station track connected to a main line by points. On a double-line
route, each direction may have its own loop:

```text
                         /---- UP_LOOP ----\
UP_MAIN   --------------<------------------>--------------  toward Churchgate

DOWN_MAIN --------------<------------------>--------------  toward Virar
                         \--- DOWN_LOOP ---/
```

- `UP_LOOP` serves UP movements and connects back to `UP_MAIN`.
- `DOWN_LOOP` serves DOWN movements and connects back to `DOWN_MAIN`.
- A station may have both loops, only one directional loop, or no loop.
- Main lines are continuous between stations; loops normally exist only within a
  station's limits.

On the old single-line model, a loop primarily enabled opposing trains to cross.
In this double-line model, opposite trains already have separate mains. A loop is
therefore modeled as an **overtaking resource**: a lower-priority train can be
received into its directional loop while a higher-priority train passes on the
directional main.

## Lines Are Not Platforms

A line is a physical track or operational route. A platform is passenger-access
infrastructure beside a line. A loop may have a platform or may be used only for
regulation, and one platform can sometimes serve tracks on both sides. The current
simulator models lines, not exact platform faces or station layouts.

## Implementation In This Branch

The `network_lines` branch introduces:

- `up_main` and `down_main` at every station;
- independently configurable `up_loop` and `down_loop` station lines;
- directional block keys such as `(2, 3, "up")`;
- explicit mapping from station-index movement to UP/DOWN;
- simultaneous opposite-direction use of parallel blocks;
- same-direction priority overtaking through a directional loop;
- occupancy snapshots that show all available directional lines.

Borivali and Andheri are configured with both directional loops. This is an
idealized project topology and is not asserted to be the exact current track layout
of those stations.

## Current Limits And Next Steps

Trains now occupy adjacent blocks for one or more 30-second ticks. SLOW and FAST
use two ticks per block, while EXPRESS uses one; stop patterns add scheduled dwell.
See [timing_model.md](timing_model.md) for the complete simplified timing model.
Actual station distances, per-block speed limits, and headway remain future work.

Mumbai's busiest corridors can also distinguish fast and slow running lines. That
future model should add explicit tracks and crossovers rather than treating a
station loop as a substitute for an entire fast/slow corridor.

## Sources

- [Northern Railway General and Subsidiary Rules, 2025](https://nr.indianrailways.gov.in/uploads/files/1747981399971-G%20and%20SR%20reprinted%20edition%202025.pdf)
- [Indian Railways Operating Manual](https://indianrailways.gov.in/railwayboard/uploads/codesmanual/operating%20manual-traffic.pdf)
- [CAMTECH Maintenance Handbook on Automatic Signalling](https://indianrailways.gov.in/railwayboard/uploads/directorate/eff_res/camtech/S&T%20Engineering/YearWise/Maintenance%20handbook%20on%20Automatic%20Signalling%20ver2(1).pdf)
- [IRFCA: Indian Railways train-number and UP/DOWN notes](https://irfca.org/faq/faq-number.html)
- [IRFCA: railway technical terminology](https://irfca.org/faq/faq-jargon2.html)
- [News18 explainer on Indian Railways UP/DOWN designation](https://www.news18.com/news/india/heres-how-the-up-and-down-direction-of-trains-decided-in-indian-railways-4130069.html)

The first three are railway-issued documents. IRFCA is a long-running enthusiast
technical reference; the News18 article is included as a readable secondary
explanation. Route-specific working documents should take precedence over any
general UP/DOWN rule.

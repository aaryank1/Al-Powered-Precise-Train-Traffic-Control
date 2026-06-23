# Model v2: Directional Double Line

The controlled section contains six ordered stations:

```text
UP:    Virar -> Bhayandar -> Borivali -> Andheri -> Bandra -> Dadar
DOWN:  Virar <- Bhayandar <- Borivali <- Andheri <- Bandra <- Dadar
```

Every station has an `up_main` and `down_main`. Borivali and Andheri also have
an `up_loop` and `down_loop`:

| Station | UP main | DOWN main | UP loop | DOWN loop |
| --- | --- | --- | --- | --- |
| Virar | yes | yes | no | no |
| Bhayandar | yes | yes | no | no |
| Borivali | yes | yes | yes | yes |
| Andheri | yes | yes | yes | yes |
| Bandra | yes | yes | no | no |
| Dadar | yes | yes | no | no |

Opposing movements use separate directional blocks. Loops support overtaking by
trains moving in the same direction. Train priorities remain:

```text
EXPRESS (10) > FAST (5) > SLOW (1)
```

See [network_lines.md](network_lines.md) for terminology, diagrams, limitations,
and research sources. See [timing_model.md](timing_model.md) for running and dwell
times, stop patterns, and the movement lifecycle.

from models.train import EXPRESS, FAST, SLOW, Train


def build_trains() -> list[Train]:
    """Create slow, fast, and express services with an UP overtake."""

    return [
        Train(
            name="UP_EXP1",
            train_type=EXPRESS,
            priority=10,
            current_station=0,
            destination_station=5,
            scheduled_stops=(2, 5),
        ),
        Train(
            name="UP_SLOW1",
            train_type=SLOW,
            priority=1,
            current_station=1,
            destination_station=5,
        ),
        Train(
            name="DOWN_FAST1",
            train_type=FAST,
            priority=5,
            current_station=5,
            destination_station=0,
            scheduled_stops=(3, 2, 0),
        ),
    ]


trains = build_trains()

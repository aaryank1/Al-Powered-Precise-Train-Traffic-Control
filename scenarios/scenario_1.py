from models.train import Train


def build_trains() -> list[Train]:
    """Create a mixed-direction scenario with one UP overtaking conflict."""

    return [
        Train(
            name="UP_EXP1",
            train_type="EXPRESS",
            priority=10,
            current_station=1,
            destination_station=5,
        ),
        Train(
            name="UP_LOC1",
            train_type="LOCAL",
            priority=1,
            current_station=2,
            destination_station=5,
        ),
        Train(
            name="DOWN_LOC1",
            train_type="LOCAL",
            priority=1,
            current_station=5,
            destination_station=0,
        ),
    ]


trains = build_trains()

from models.train import Train


def build_trains() -> list[Train]:
    """
    Create a scenario :
    Create the default express/local crossing scenario.

    Returns:
        A list of trains
    """

    return [
        Train(
            name="EXP1",
            train_type="EXPRESS",
            priority=10,
            current_station=0,
            destination_station=5,
        ),
        Train(
            name="LOC1",
            train_type="LOCAL",
            priority=1,
            current_station=5,
            destination_station=0,
        ),
    ]


trains = build_trains()

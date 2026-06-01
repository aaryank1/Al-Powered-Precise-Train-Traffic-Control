from models.train import Train

trains = [
    Train(
        name="EXP1",
        train_type="EXPRESS",
        priority=10,
        current_station=0,
        destination_station=5
    ),
    Train(
        name="LOC1",
        train_type="LOCAL",
        priority=1,
        current_station=5,
        destination_station=0
    )
]
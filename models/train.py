from dataclasses import dataclass

@dataclass
class Train:
    name: str
    train_type: str
    priority: int

    current_station: int
    destination_station: int

    waiting_time: int = 0
    finished: bool = False

    def direction(self):
        if self.destination_station > self.current_station:
            return 1
        return -1
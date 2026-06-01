from src.network import stations

class Simulator:
    
    def __init__(self, trains, scheduler):

        self.trains = trains
        self.scheduler = scheduler

        self.time = 0

    def step(self):

        print(f"\nTIME {self.time}")

        move_order = self.scheduler.decide_moves(self.trains)

        occupied = set()

        for train in move_order:
            if train.finished:
                continue

            next_station = (train.current_station + train.direction())
            
            if next_station in occupied:
                print(
                    f"{train.name} waiting"
                )
                train.waiting_time += 1
                continue

            occupied.add(next_station)

            print(
                f"{train.name}: "
                f"{stations[train.current_station].name}"
                f" -> "
                f"{stations[next_station].name}"
            )

            train.current_station = next_station

            if (train.current_station == train.destination_station):
                train.finished = True
                print(
                    f"{train.name} arrived"
                )

        self.time += 1
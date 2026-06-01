class Scheduler:
    def decide_moves(self, trains):
        active = [
            t for t in trains
            if not t.finished
        ]
        active.sort(
            key=lambda x: x.priority,
            reverse=True
        )
        return active
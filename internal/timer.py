from internal.profiler import profiler
import time


class Timer:
    @profiler
    def __init__(self, duration: float):
        self.duration = duration
        self.startedAt = time.time()
        self.doneAt = self.startedAt + self.duration

    @profiler
    def done(self) -> bool:
        return time.time() >= self.doneAt

    @profiler
    def progress(self) -> float:
        return (time.time() - self.startedAt) / self.duration

    @profiler
    def restart(self):
        self.startedAt = time.time()
        self.doneAt = self.startedAt + self.duration
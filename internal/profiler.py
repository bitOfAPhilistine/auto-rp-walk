import time


class ProfilerStats:
    def __init__(self):
        self.callCount: int = 0
        self.totalTime: float = 0.0
        self.avgTime: float = 0.0
        self.maxTime: float = 0.0
        self.children: dict[function] = {}

profiling = False
mainTimes: dict[function, ProfilerStats] = {}
frameTimes: dict[function, ProfilerStats] = {}
funcStack: list[function] = []

def profiler(func):
    def inner(*args, **kwargs):
        if profiling and (len(funcStack) == 0 or funcStack[-1] != func):
            mainTimes: dict[function, ProfilerStats] = mainTimes
            frameTimes: dict[function, ProfilerStats] = frameTimes

            try:
                for parent in funcStack:
                    mainTimes = mainTimes[parent].children
            except Exception as e:
                print(funcStack)
                print(mainTimes)
                print(frameTimes)
                raise e

            if func not in mainTimes:
                mainTimes[func] = ProfilerStats()
            
            if func not in frameTimes:
                frameTimes[func] = ProfilerStats()
            
            funcStack.append(func)

            startTime = time.time()
            result = func(*args, **kwargs)
            timeTaken = time.time() - startTime
            
            mainTimes[func].callCount += 1
            mainTimes[func].totalTime += timeTaken
            mainTimes[func].avgTime = mainTimes[func].totalTime / mainTimes[func].callCount
            if timeTaken > mainTimes[func].maxTime:
                mainTimes[func].maxTime = timeTaken
            
            frameTimes[func].callCount += 1
            frameTimes[func].totalTime += timeTaken

            funcStack.pop()

            return result
        
        return func(*args, **kwargs)

    return inner

def save(path: str):
    if len(mainTimes) > 0:
        with open(path, 'w') as f:
            f.write(profilerTimes_to_string(mainTimes))


def profilerTimes_to_string(times, parentTotal = 1.0, depth = 0) -> str:
    output: str = ""
    sortedTimes = sorted(times, key=lambda x: times[x].totalTime, reverse=True)
    for func in sortedTimes:
        data = times[func]
        output += f"{"  " * depth}{func.__qualname__}: called {data.callCount} times, total {data.totalTime}s taken, average {data.avgTime}s, max {data.maxTime}{f", percentage of parent time: {data.totalTime / parentTotal * 100.0:.2f}%" if depth > 0 else ''}\n"
        if len(data.children) > 0:
            output += profilerTimes_to_string(data.children, data.totalTime, depth + 1)
    return output
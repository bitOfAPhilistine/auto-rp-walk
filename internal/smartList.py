from internal.profiler import profiler


class SmartList(list):
    @profiler
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._freedIndices = []

    @profiler
    def add(self, item) -> int:
        if len(self._freedIndices) > 0:
            index = self._freedIndices.pop(0)
            if self[index] is not None:
                raise ValueError("Index is freed but still occupied")
            self[index] = item
            return index
        else:
            self.append(item)
            return len(self) - 1
    
    @profiler
    def remove(self, index: int):
        if index < 0 or index >= len(self):
            raise IndexError("Index out of bounds")

        if index == len(self) - 1:
            self.pop()

            if len(self) > 0 and self[len(self) - 1] is None:
                self._freedIndices.pop(self._freedIndices.index(len(self) - 1))
                self.remove(len(self) - 1)
            
            return
        
        self._freedIndices.append(index)
        self[index] = None
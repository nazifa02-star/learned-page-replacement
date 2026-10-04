from collections import deque


def fifo(references, frames):
    memory = []
    queue = deque()
    faults = 0

    for page in references:
        if page in memory:
            continue

        faults += 1

        if len(memory) >= frames:
            victim = queue.popleft()
            memory.remove(victim)

        memory.append(page)
        queue.append(page)

    return faults


def lru(references, frames):
    memory = []
    last_used = {}
    faults = 0

    for i, page in enumerate(references):
        if page in memory:
            last_used[page] = i
            continue

        faults += 1

        if len(memory) >= frames:
            victim = min(memory, key=lambda p: last_used[p])
            memory.remove(victim)
            del last_used[victim]

        memory.append(page)
        last_used[page] = i

    return faults


def optimal(references, frames):
    memory = []
    faults = 0

    for i, page in enumerate(references):
        if page in memory:
            continue

        faults += 1

        if len(memory) >= frames:
            future = references[i + 1:]

            def next_use(p):
                try:
                    return future.index(p)
                except ValueError:
                    return float("inf")

            victim = max(memory, key=next_use)
            memory.remove(victim)

        memory.append(page)

    return faults


if __name__ == "__main__":
    test_trace = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
    frames = 3

    print("Validation trace:", test_trace)
    print("Frames:", frames)
    print("FIFO faults:", fifo(test_trace, frames))
    print("LRU faults:", lru(test_trace, frames))
    print("Optimal faults:", optimal(test_trace, frames))

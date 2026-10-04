import random


def generate_workload(seed=42, total_references=1000, shift_point=500):
    """
    Generate a workload with a deliberate distribution shift.

    Phase 1:
        Locality-heavy workload with a small hot set.

    Phase 2:
        Random/bursty workload over a larger page pool.
    """
    random.seed(seed)

    phase1 = []
    hot_pages = [0, 1, 2, 3, 4, 5]

    for i in range(shift_point):
        if i % 10 < 8:
            phase1.append(random.choice(hot_pages))
        else:
            phase1.append(random.randint(6, 15))

    phase2 = []
    large_pool = list(range(0, 50))

    while len(phase2) < total_references - shift_point:
        burst_page = random.choice(large_pool)

        for _ in range(random.randint(1, 4)):
            if len(phase2) >= total_references - shift_point:
                break

            phase2.append(burst_page)

        for _ in range(random.randint(1, 3)):
            if len(phase2) >= total_references - shift_point:
                break

            phase2.append(random.choice(large_pool))

    references = phase1 + phase2

    return references[:total_references]


if __name__ == "__main__":
    workload = generate_workload()

    print("Total references:", len(workload))
    print("Shift point:", 500)
    print("First 20 references:", workload[:20])
    print("References around shift:", workload[490:510])
    print("Last 20 references:", workload[-20:])

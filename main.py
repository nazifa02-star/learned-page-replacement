import csv
import random

from src.workload import generate_workload
from src.policies import fifo, lru, optimal
from src.learned_policy import LearnedPolicy


FRAMES = 4
TOTAL_REFERENCES = 1000
SHIFT_POINT = 500
SEED = 42


def generate_training_traces(
    number_of_traces=80,
    trace_length=1000,
    seed=123
):
    """
    Generate separate traces for training the learned model.

    These traces are different from the evaluation workload.
    """

    rng = random.Random(seed)
    traces = []

    for _ in range(number_of_traces):

        trace = []

        hot_pages = list(range(rng.randint(4, 8)))
        large_pool = list(range(50))

        for i in range(trace_length):

            if i < trace_length // 2:

                # Locality-heavy phase
                if rng.random() < 0.80:
                    trace.append(rng.choice(hot_pages))
                else:
                    trace.append(rng.randint(8, 20))

            else:

                # Random/bursty phase
                if rng.random() < 0.60:
                    page = rng.choice(large_pool)
                    burst_length = rng.randint(1, 3)

                    for _ in range(burst_length):
                        if len(trace) < trace_length:
                            trace.append(page)
                else:
                    trace.append(rng.choice(large_pool))

        traces.append(trace[:trace_length])

    return traces


def simulate_fifo_with_phases(references, frames):
    """
    Run FIFO continuously over the complete trace and record
    faults before and after the workload shift.
    """

    memory = []
    queue = []
    fault_indices = []

    for i, page in enumerate(references):

        if page in memory:
            continue

        fault_indices.append(i)

        if len(memory) >= frames:
            victim = queue.pop(0)
            memory.remove(victim)

        memory.append(page)
        queue.append(page)

    before_faults = sum(
        1 for i in fault_indices if i < SHIFT_POINT
    )

    after_faults = sum(
        1 for i in fault_indices if i >= SHIFT_POINT
    )

    total_faults = len(fault_indices)

    return {
        "before_faults": before_faults,
        "after_faults": after_faults,
        "total_faults": total_faults,
        "before_hit_rate": (SHIFT_POINT - before_faults) / SHIFT_POINT,
        "after_hit_rate": (
            (len(references) - SHIFT_POINT) - after_faults
        ) / (len(references) - SHIFT_POINT),
        "overall_hit_rate": (
            len(references) - total_faults
        ) / len(references)
    }


def simulate_lru_with_phases(references, frames):
    """
    Run LRU continuously over the complete trace and record
    faults before and after the workload shift.
    """

    memory = []
    last_used = {}
    fault_indices = []

    for i, page in enumerate(references):

        if page in memory:
            last_used[page] = i
            continue

        fault_indices.append(i)

        if len(memory) >= frames:
            victim = min(
                memory,
                key=lambda p: last_used[p]
            )

            memory.remove(victim)
            del last_used[victim]

        memory.append(page)
        last_used[page] = i

    before_faults = sum(
        1 for i in fault_indices if i < SHIFT_POINT
    )

    after_faults = sum(
        1 for i in fault_indices if i >= SHIFT_POINT
    )

    total_faults = len(fault_indices)

    return {
        "before_faults": before_faults,
        "after_faults": after_faults,
        "total_faults": total_faults,
        "before_hit_rate": (SHIFT_POINT - before_faults) / SHIFT_POINT,
        "after_hit_rate": (
            (len(references) - SHIFT_POINT) - after_faults
        ) / (len(references) - SHIFT_POINT),
        "overall_hit_rate": (
            len(references) - total_faults
        ) / len(references)
    }


def simulate_optimal_with_phases(references, frames):
    """
    Run Optimal continuously over the complete trace and record
    faults before and after the workload shift.
    """

    memory = []
    fault_indices = []

    for i, page in enumerate(references):

        if page in memory:
            continue

        fault_indices.append(i)

        if len(memory) >= frames:

            future = references[i + 1:]

            def next_use(p):
                try:
                    return future.index(p)
                except ValueError:
                    return float("inf")

            victim = max(
                memory,
                key=next_use
            )

            memory.remove(victim)

        memory.append(page)

    before_faults = sum(
        1 for i in fault_indices if i < SHIFT_POINT
    )

    after_faults = sum(
        1 for i in fault_indices if i >= SHIFT_POINT
    )

    total_faults = len(fault_indices)

    return {
        "before_faults": before_faults,
        "after_faults": after_faults,
        "total_faults": total_faults,
        "before_hit_rate": (SHIFT_POINT - before_faults) / SHIFT_POINT,
        "after_hit_rate": (
            (len(references) - SHIFT_POINT) - after_faults
        ) / (len(references) - SHIFT_POINT),
        "overall_hit_rate": (
            len(references) - total_faults
        ) / len(references)
    }


def evaluate_classical(references, policy_name):
    """
    Evaluate a classical policy continuously over the full
    workload so that memory state is preserved across the shift.
    """

    if policy_name == "FIFO":
        return simulate_fifo_with_phases(
            references,
            FRAMES
        )

    if policy_name == "LRU":
        return simulate_lru_with_phases(
            references,
            FRAMES
        )

    if policy_name == "Optimal":
        return simulate_optimal_with_phases(
            references,
            FRAMES
        )

    raise ValueError(f"Unknown policy: {policy_name}")


def evaluate_learned(references, policy):
    """
    Evaluate learned policy before and after shift.

    The policy is trained only on separate training traces.
    """

    result = policy.evaluate(references)

    before_faults = 0
    after_faults = 0

    for decision in result["decisions"]:

        if decision["index"] < SHIFT_POINT:
            before_faults += 1
        else:
            after_faults += 1

    before_hits = SHIFT_POINT - before_faults

    after_hits = (
        len(references) - SHIFT_POINT
    ) - after_faults

    return {
        "before_faults": before_faults,
        "after_faults": after_faults,
        "total_faults": result["faults"],
        "before_hit_rate": before_hits / SHIFT_POINT,
        "after_hit_rate": (
            after_hits /
            (len(references) - SHIFT_POINT)
        ),
        "overall_hit_rate": result["hit_rate"]
    }


def save_results(results):
    """
    Save experimental results as CSV.
    """

    filename = "results/results.csv"

    fields = [
        "policy",
        "before_faults",
        "after_faults",
        "total_faults",
        "before_hit_rate",
        "after_hit_rate",
        "overall_hit_rate"
    ]

    with open(filename, "w", newline="") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()

        for row in results:
            writer.writerow(row)

    print(f"\nResults saved to {filename}")


def main():

    print("=" * 60)
    print("Learned Page Replacement Experiment")
    print("=" * 60)

    # ---------------------------------------------------------
    # Evaluation workload
    # ---------------------------------------------------------

    references = generate_workload(
        seed=SEED,
        total_references=TOTAL_REFERENCES,
        shift_point=SHIFT_POINT
    )

    print(f"References: {len(references)}")
    print(f"Frames: {FRAMES}")
    print(f"Shift point: {SHIFT_POINT}")

    # ---------------------------------------------------------
    # Training data
    # ---------------------------------------------------------

    print("\nGenerating training traces...")

    training_traces = generate_training_traces(
        number_of_traces=80,
        trace_length=1000,
        seed=123
    )

    learned = LearnedPolicy(frames=FRAMES)

    training_examples = learned.train(
        training_traces
    )

    print("Training traces:", len(training_traces))
    print("Training examples:", training_examples)

    # ---------------------------------------------------------
    # Classical policies
    # ---------------------------------------------------------

    print("\nRunning classical policies...")

    results = []

    classical_policies = [
        "FIFO",
        "LRU",
        "Optimal"
    ]

    for name in classical_policies:

        result = evaluate_classical(
            references,
            name
        )

        result["policy"] = name
        results.append(result)

    # ---------------------------------------------------------
    # Learned policy
    # ---------------------------------------------------------

    print("Running learned policy...")

    learned_result = evaluate_learned(
        references,
        learned
    )

    learned_result["policy"] = "Learned"
    results.append(learned_result)

    # ---------------------------------------------------------
    # Print results
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("EXPERIMENT RESULTS")
    print("=" * 60)

    print(
        f"{'Policy':<12}"
        f"{'Before Faults':<16}"
        f"{'After Faults':<15}"
        f"{'Total Faults':<15}"
        f"{'Overall Hit':<12}"
    )

    print("-" * 70)

    for result in results:

        print(
            f"{result['policy']:<12}"
            f"{result['before_faults']:<16}"
            f"{result['after_faults']:<15}"
            f"{result['total_faults']:<15}"
            f"{result['overall_hit_rate']:.3f}"
        )

    # ---------------------------------------------------------
    # Save CSV
    # ---------------------------------------------------------

    save_results(results)


if __name__ == "__main__":
    main()

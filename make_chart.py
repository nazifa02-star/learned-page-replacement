import csv
import matplotlib.pyplot as plt


policies = []
before = []
after = []

with open("results/results.csv", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        policies.append(row["policy"])
        before.append(int(row["before_faults"]))
        after.append(int(row["after_faults"]))


x = range(len(policies))
width = 0.35

plt.figure(figsize=(9, 5))

plt.bar(
    [i - width / 2 for i in x],
    before,
    width=width,
    label="Before Shift"
)

plt.bar(
    [i + width / 2 for i in x],
    after,
    width=width,
    label="After Shift"
)

plt.xticks(list(x), policies)
plt.xlabel("Page Replacement Policy")
plt.ylabel("Page Fault Count")
plt.title("Page Faults Before and After Workload Shift")
plt.legend()
plt.tight_layout()

plt.savefig("results/page_faults_shift.png", dpi=200)

print("Chart saved to results/page_faults_shift.png")

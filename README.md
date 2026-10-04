# Learned Page Replacement Under Workload Shift

## CSE-307 Operating System — Term Paper
### Track 1: Memory Management

**Student:** Nazifa Rahman  
**Student ID:** 202414047  
**Course:** CSE-307, Operating System  
**Teacher:** Lec. Khaled Hasan Irfan  

---

## 1. Problem Statement

Page replacement is an important part of operating system memory management. When all available memory frames are occupied and a new page is requested, the operating system must decide which existing page should be removed.

Classical page replacement algorithms such as FIFO and LRU use fixed rules. However, real workloads can change their access patterns over time.

This project investigates whether a lightweight learned page replacement policy can respond to such workload changes.

The experiment compares:

- FIFO
- LRU
- Optimal (Belady's algorithm)
- A learned page replacement policy using a Decision Tree classifier

A deliberate workload shift is introduced halfway through the reference sequence:

- First half: locality-heavy workload
- Second half: random/bursty workload

The main measurements are page-fault count and hit ratio before and after the workload shift.

---

## 2. Objectives

The main objectives are:

1. Implement classical FIFO, LRU, and Optimal page replacement algorithms.
2. Implement a lightweight learned eviction policy.
3. Use workload features such as recency and access frequency for prediction.
4. Generate a synthetic workload with a deliberate distribution shift.
5. Compare page faults and hit ratios before and after the shift.
6. Analyze how each policy behaves when the workload pattern changes.

---

## 3. Algorithms

### FIFO

FIFO (First-In, First-Out) removes the page that has been in memory for the longest time.

A queue is used to maintain the order of page insertion.

### LRU

LRU (Least Recently Used) removes the page that has not been used for the longest time.

The implementation keeps track of the most recent access position of each resident page.

### Optimal

Optimal page replacement removes the resident page whose next use is farthest in the future.

It is used as an ideal reference policy because it requires knowledge of future references.

### Learned Policy

The learned policy uses a lightweight Decision Tree classifier.

For each eviction decision, the policy considers four past-only features:

1. Normalized recency
2. Recent access frequency
3. Historical access frequency
4. Recent working-set ratio

The evaluation features do not use future references.

Future information is used only when creating training labels for the separate training data.

The model configuration is:

- Decision Tree classifier
- Maximum depth: 6
- Minimum samples per leaf: 15
- Balanced class weights
- Random state: 42

---

## 4. Workload Generation

The evaluation workload contains:

- Total references: 1000
- Number of frames: 4
- Shift point: 500
- Random seed: 42

### Phase 1 — Locality-Heavy

The first 500 references mostly access a small hot set of pages.

This creates temporal locality.

### Phase 2 — Random/Bursty

The second 500 references use a larger page pool and include short bursts of repeated accesses.

This creates a different access distribution from Phase 1.

The shift occurs exactly at reference 500.

---

## 5. Training Setup

The learned model is trained using separate synthetic traces rather than the evaluation trace.

Training configuration:

- Training traces: 80
- Trace length: 1000 references
- Training seed: 123
- Training examples: 62,404

The evaluation workload is kept separate from the training data to avoid using the evaluation trace as training input.

---

## 6. Experimental Results

The experiment produced the following results:

| Policy | Before Faults | After Faults | Total Faults | Before Hit | After Hit | Overall Hit |
|--------|--------------:|-------------:|-------------:|-----------:|----------:|------------:|
| FIFO | 306 | 303 | 609 | 38.8% | 39.4% | 39.1% |
| LRU | 295 | 301 | 596 | 41.0% | 39.8% | 40.4% |
| Optimal | 179 | 242 | 421 | 64.2% | 51.6% | 57.9% |
| Learned | 260 | 306 | 566 | 48.0% | 38.8% | 43.4% |

The complete numerical results are stored in:

`results/results.csv`

The comparison chart is stored in:

`results/page_faults_shift.png`

---

## 7. Results Analysis

### FIFO

FIFO produced 609 total page faults and an overall hit ratio of 39.1%.

Its page-fault count changed from 306 before the shift to 303 after the shift. In this particular workload, the two phases produced similar FIFO performance.

### LRU

LRU produced 596 total page faults and an overall hit ratio of 40.4%.

Its faults increased slightly from 295 to 301 after the workload shift.

### Optimal

Optimal achieved the best result with only 421 total page faults and a 57.9% overall hit ratio.

Its hit ratio decreased from 64.2% to 51.6% after the shift. This is expected because the second phase has a larger and more random access space, making reuse less predictable.

Optimal still performs best because it has access to future references.

### Learned Policy

The learned policy produced 566 total page faults and an overall hit ratio of 43.4%.

Before the shift, it achieved 260 faults and a 48.0% hit ratio.

After the shift, its faults increased to 306 and its hit ratio decreased to 38.8%.

This shows that the learned policy can outperform FIFO and LRU overall in this experiment, but its learned eviction behavior does not fully generalize to the changed workload distribution.

The learned policy therefore shows partial benefit from using workload features, while also demonstrating the limitation of a model trained on a particular distribution.

---

## 8. Shift Analysis

The workload shift changes the reference behavior from a small locality-heavy page set to a larger random/bursty page pool.

The main observations are:

- Optimal remains the strongest policy overall.
- Learned performs better overall than FIFO and LRU.
- Learned has 43.4% overall hit ratio compared with 39.1% for FIFO and 40.4% for LRU.
- The learned policy's hit ratio drops from 48.0% to 38.8% after the shift.
- The learned model therefore shows sensitivity to distribution shift.
- The experiment demonstrates why adaptive OS heuristics may need retraining or additional mechanisms when workload behavior changes.

The result also shows the trade-off between a fixed classical rule and a learned heuristic. A learned policy can use multiple workload signals, but its performance depends on how well those signals generalize to unseen workload patterns.

---

## 9. Validation of Classical Algorithms

A deterministic validation trace was used:

```text
[7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]

from collections import Counter, deque
from sklearn.tree import DecisionTreeClassifier


class LearnedPolicy:
    """
    Lightweight learned page-replacement policy.

    The model predicts which resident page is a good eviction
    candidate using only information available up to the current
    reference.

    Features:
        1. Normalized recency
        2. Recent frequency
        3. Historical frequency
        4. Recent working-set ratio
    """

    def __init__(self, frames=4):
        self.frames = frames

        self.model = DecisionTreeClassifier(
            max_depth=6,
            min_samples_leaf=15,
            class_weight="balanced",
            random_state=42
        )

        self.history = []
        self.last_used = {}
        self.total_frequency = Counter()
        self.recent_window = deque(maxlen=20)

        self.trained = False

    # ---------------------------------------------------------
    # Feature extraction
    # ---------------------------------------------------------

    def _features(self, page, current_index):
        """
        Create four past-only features for a resident page.
        """

        # Feature 1: normalized recency
        if page in self.last_used:
            recency = current_index - self.last_used[page]
        else:
            recency = current_index + 1

        normalized_recency = recency / max(current_index + 1, 1)

        # Feature 2: frequency in recent 20 references
        recent_frequency = self.recent_window.count(page)

        # Feature 3: historical frequency
        historical_frequency = self.total_frequency[page]

        total_recent = len(self.recent_window)

        # Feature 4: recent working-set ratio
        if total_recent > 0:
            unique_recent = len(set(self.recent_window))
            working_set_ratio = unique_recent / total_recent
        else:
            working_set_ratio = 0.0

        return [
            normalized_recency,
            recent_frequency,
            historical_frequency,
            working_set_ratio
        ]

    # ---------------------------------------------------------
    # Training data generation
    # ---------------------------------------------------------

    def _build_training_data(self, training_traces, future_window=20):
        """
        Generate training examples.

        The future is used ONLY to create training labels.
        It is never used as an evaluation feature.

        Label:
            1 -> page is a good eviction candidate
            0 -> page should preferably stay
        """

        X = []
        y = []

        for trace in training_traces:

            history = []
            last_used = {}
            total_frequency = Counter()
            recent_window = deque(maxlen=20)

            for i, current_page in enumerate(trace):

                # Candidate pages are pages currently in memory.
                resident_pages = list(dict.fromkeys(history[-self.frames:]))

                if current_page not in resident_pages and len(resident_pages) >= self.frames:

                    for candidate in resident_pages:

                        # -----------------------------
                        # Past-only features
                        # -----------------------------

                        if candidate in last_used:
                            recency = i - last_used[candidate]
                        else:
                            recency = i + 1

                        normalized_recency = recency / max(i + 1, 1)

                        recent_frequency = recent_window.count(candidate)

                        historical_frequency = total_frequency[candidate]

                        if len(recent_window) > 0:
                            unique_recent = len(set(recent_window))
                            working_set_ratio = (
                                unique_recent / len(recent_window)
                            )
                        else:
                            working_set_ratio = 0.0

                        X.append([
                            normalized_recency,
                            recent_frequency,
                            historical_frequency,
                            working_set_ratio
                        ])

                        # -----------------------------
                        # Future ONLY for label
                        # -----------------------------

                        future = trace[
                            i + 1:min(len(trace), i + 1 + future_window)
                        ]

                        if candidate not in future:
                            label = 1
                        else:
                            candidate_next_use = future.index(candidate)

                            # Compare candidate with other residents.
                            other_next_uses = []

                            for other in resident_pages:
                                if other == candidate:
                                    continue

                                if other in future:
                                    other_next_uses.append(
                                        future.index(other)
                                    )
                                else:
                                    other_next_uses.append(float("inf"))

                            if other_next_uses:
                                label = int(
                                    candidate_next_use >= max(other_next_uses)
                                )
                            else:
                                label = 1

                        y.append(label)

                # Update history AFTER feature creation.
                history.append(current_page)
                last_used[current_page] = i
                total_frequency[current_page] += 1
                recent_window.append(current_page)

        return X, y

    # ---------------------------------------------------------
    # Train
    # ---------------------------------------------------------

    def train(self, training_traces):
        """
        Train the Decision Tree using separate training traces.
        """

        X, y = self._build_training_data(training_traces)

        if not X:
            raise ValueError("No training examples were generated.")

        if len(set(y)) < 2:
            raise ValueError("Training data must contain both classes.")

        self.model.fit(X, y)
        self.trained = True

        return len(X)

    # ---------------------------------------------------------
    # Prediction
    # ---------------------------------------------------------

    def predict_eviction_candidate(self, resident_pages, current_index):
        """
        Predict which resident page should be evicted.
        """

        if not resident_pages:
            return None

        if not self.trained:
            raise RuntimeError(
                "Model is not trained. Call train() first."
            )

        candidates = []

        for page in resident_pages:
            features = self._features(page, current_index)

            probability = self.model.predict_proba(
                [features]
            )[0]

            # Probability of class 1 = eviction candidate.
            if len(probability) == 2:
                eviction_probability = probability[1]
            else:
                eviction_probability = 0.0

            candidates.append(
                (eviction_probability, features[0], page)
            )

        # Highest eviction probability wins.
        # If tied, larger recency wins.
        candidates.sort(
            key=lambda x: (x[0], x[1]),
            reverse=True
        )

        return candidates[0][2]

    # ---------------------------------------------------------
    # Evaluate complete trace
    # ---------------------------------------------------------

    def evaluate(self, references):
        """
        Run the learned page replacement policy.

        Returns:
            faults
            hits
            hit_rate
        """

        if not self.trained:
            raise RuntimeError(
                "Model is not trained. Call train() first."
            )

        memory = []

        faults = 0
        hits = 0

        decisions = []

        # Reset runtime statistics.
        self.history = []
        self.last_used = {}
        self.total_frequency = Counter()
        self.recent_window = deque(maxlen=20)

        for i, page in enumerate(references):

            # -----------------------------
            # HIT
            # -----------------------------

            if page in memory:
                hits += 1

            # -----------------------------
            # PAGE FAULT
            # -----------------------------

            else:
                faults += 1

                victim = None

                if len(memory) >= self.frames:
                    victim = self.predict_eviction_candidate(
                        memory,
                        i
                    )

                    memory.remove(victim)

                memory.append(page)

                decisions.append({
                    "index": i,
                    "page": page,
                    "victim": victim,
                    "frames": list(memory)
                })

            # Update statistics AFTER processing reference.
            self.history.append(page)
            self.last_used[page] = i
            self.total_frequency[page] += 1
            self.recent_window.append(page)

        total = len(references)

        hit_rate = hits / total if total else 0.0

        return {
            "faults": faults,
            "hits": hits,
            "hit_rate": hit_rate,
            "decisions": decisions
        }


# =============================================================
# Simple standalone test
# =============================================================

if __name__ == "__main__":

    print("Learned Page Replacement Policy")
    print("--------------------------------")

    # Small separate training traces.
    training_traces = [
        [
            0, 1, 2, 0, 1, 3, 0, 1, 2, 0,
            4, 0, 1, 2, 3, 0, 1, 5
        ],
        [
            2, 3, 4, 2, 3, 5, 2, 3, 4, 2,
            6, 2, 3, 4, 5, 2, 3, 7
        ],
        [
            0, 1, 0, 2, 1, 0, 3, 1, 0, 2,
            4, 0, 1, 2, 3, 0, 1, 5
        ]
    ]

    policy = LearnedPolicy(frames=4)

    examples = policy.train(training_traces)

    print("Training examples:", examples)
    print("Model trained:", policy.trained)

    test_trace = [
        0, 1, 2, 3,
        0, 1, 4, 5,
        0, 1, 2, 6,
        7, 8, 9, 0
    ]

    result = policy.evaluate(test_trace)

    print("References:", len(test_trace))
    print("Hits:", result["hits"])
    print("Page Faults:", result["faults"])
    print("Hit Rate:", round(result["hit_rate"] * 100, 2), "%")

    print("\nLast 5 decisions:")

    for decision in result["decisions"][-5:]:
        print(
            "Index:",
            decision["index"],
            "| Page:",
            decision["page"],
            "| Victim:",
            decision["victim"],
            "| Frames:",
            decision["frames"]
        )

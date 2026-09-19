# KOYLA Topic Trend Classification Rules

## 1. Overview & Disclaimer

This document defines the deterministic analytical rules implemented in KOYLA for tracking and classifying temporal topic dynamics across Indian coal mining statutory documents.

> [!IMPORTANT]
> **Methodological Disclaimer**:
> These rules are **deterministic analytical classifications** configured within KOYLA based on observable document shares, percentage-point shifts, and minimum evidence thresholds. They are **not** statistically validated time-series forecast models, p-value tests, or causal predictions. KOYLA reports observed empirical shifts without attributing operational causation or predicting future behavior.

---

## 2. Topic Alignment Strategy

To maintain mathematical validity across multi-period comparisons:
1. **Single Global Topic Model**: A single unified topic discovery run is performed over the aggregated multi-period/multi-organization corpus using the Phase 8.2 engine.
2. **Stable Identifiers**: Each topic retains a stable identifier ($Topic_0, Topic_1, \dots$) and term vocabulary.
3. **Partitioned Aggregation**: The corpus items assigned to each topic are subsequently partitioned by fiscal year, date range, organization, mine, block, and document type.
4. **Independent runs are never cross-compared**: Topic IDs from distinct, disconnected model executions are mathematically incomparable and are never correlated.

---

## 3. Core Metrics & Mathematical Formulations

For any topic $T$ and discrete period $t$ (e.g. fiscal year $FY2024-25$):

### 3.1 Primary Metric: Document Share Percentage
$$\text{Share}_{\text{doc}}(T, t) = \left(\frac{D(T, t)}{N_{\text{doc}}(t)}\right) \times 100\%$$
- $D(T, t)$: Number of unique documents in period $t$ containing evidence belonging to topic $T$.
- $N_{\text{doc}}(t)$: Total number of analyzed documents in period $t$ within the corpus.
- **Rule**: Percentages are **never** presented without their underlying numerator $D(T, t)$ and denominator $N_{\text{doc}}(t)$.

### 3.2 Secondary Metric: Chunk Share Percentage
$$\text{Share}_{\text{chunk}}(T, t) = \left(\frac{C(T, t)}{N_{\text{chunk}}(t)}\right) \times 100\%$$
- $C(T, t)$: Number of chunks in period $t$ assigned to topic $T$.
- $N_{\text{chunk}}(t)$: Total number of analyzed chunks in period $t$ within the corpus.

### 3.3 Period-to-Period Shifts ($t_{k-1} \to t_k$)
1. **Absolute Change** ($\Delta_{\text{abs}}$):
   $$\Delta_{\text{abs}} = D(T, t_k) - D(T, t_{k-1})$$
2. **Percentage-Point Change** ($\Delta_{\text{pp}}$):
   $$\Delta_{\text{pp}} = \text{Share}_{\text{doc}}(T, t_k) - \text{Share}_{\text{doc}}(T, t_{k-1})$$
3. **Relative Percentage Growth** ($g_{\text{rel}}$):
   $$g_{\text{rel}} = \begin{cases} \left(\frac{\text{Share}_{\text{doc}}(T, t_k) - \text{Share}_{\text{doc}}(T, t_{k-1})}{\text{Share}_{\text{doc}}(T, t_{k-1})}\right) \times 100\% & \text{if } \text{Share}_{\text{doc}}(T, t_{k-1}) > 0 \\ \text{undefined or } 0.0 & \text{otherwise} \end{cases}$$

> [!NOTE]
> $\Delta_{\text{abs}}$, $\Delta_{\text{pp}}$, and $g_{\text{rel}}$ represent distinct dimensions of change and are never conflated in reports.

---

## 4. Minimum-Evidence Gates

To prevent tiny sample artifacts (e.g. 1 document out of 2 shifting from 50% to 100%) from triggering false classifications, all trend evaluations pass through strict evidence gates:

| Parameter | Default Value | Description |
|---|---|---|
| `minimum_period_documents` | `5` | Minimum total documents required in each compared period |
| `minimum_topic_documents` | `2` | Minimum documents required for a topic to establish presence |
| `minimum_comparable_periods` | `2` | Minimum consecutive/observed periods required to evaluate a trend |
| `percentage_point_threshold` | `2.0` | Minimum $\lvert\Delta_{\text{pp}}\rvert$ required to classify growth or decline |

If any compared period fails the evidence gate:
$$\text{trend\_status} = \mathbf{INSUFFICIENT\_HISTORY}$$

---

## 5. Trend Classifications

When evidence gates are satisfied across chronological periods $t_1, t_2, \dots, t_K$ ($K \ge 2$):

### 5.1 `EMERGING`
- **Conditions**:
  1. $K \ge 2$ periods.
  2. In earlier period(s) ($t_1, \dots, t_{K-1}$), topic document count is negligible ($D(T, t) = 0$ or $\text{Share}_{\text{doc}} < 1.0\%$).
  3. In later period(s) ($t_K$), topic document count meets threshold: $D(T, t_K) \ge \text{minimum\_topic\_documents}$.
  4. Both earlier and later periods satisfy `minimum_period_documents`.
- **Interpretation**: A topic newly surfacing with verified document evidence after prior absence.

### 5.2 `DISAPPEARING`
- **Conditions**:
  1. In earlier period(s) ($t_{K-1}$ or earlier), topic had verified presence ($D(T, t_{K-1}) \ge \text{minimum\_topic\_documents}$).
  2. In the latest period ($t_K$), topic document count drops to zero ($D(T, t_K) = 0$).
  3. Period $t_K$ satisfies `minimum_period_documents` (ensuring absence is not an artifact of an empty corpus).
- **Interpretation**: A previously established topic that is no longer detected in current reporting.

### 5.3 `GROWING`
- **Conditions**:
  1. Does not meet `EMERGING`.
  2. Topic is present in both periods.
  3. Net percentage-point change exceeds positive threshold: $\Delta_{\text{pp}} > +\text{percentage\_point\_threshold}$ ($+2.0$ pp).
  4. Both periods satisfy `minimum_topic_documents` and `minimum_period_documents`.
- **Interpretation**: Topic prevalence expands as a proportion of statutory reporting.

### 5.4 `DECLINING`
- **Conditions**:
  1. Does not meet `DISAPPEARING`.
  2. Topic is present in both periods.
  3. Net percentage-point change exceeds negative threshold: $\Delta_{\text{pp}} < -\text{percentage\_point\_threshold}$ ($-2.0$ pp).
  4. Both periods satisfy `minimum_period_documents`.
- **Interpretation**: Topic prevalence contracts as a proportion of statutory reporting.

### 5.5 `STABLE`
- **Conditions**:
  1. Topic is present across periods.
  2. Absolute percentage-point change is within tolerance: $\lvert\Delta_{\text{pp}}\rvert \le \text{percentage\_point\_threshold}$ ($2.0$ pp).
  3. Both periods satisfy evidence gates.
- **Interpretation**: Topic reporting frequency remains steady over time.

### 5.6 `RECURRING`
- **Conditions**:
  1. Requires $K \ge 3$ periods.
  2. Topic exhibits the chronological pattern: $\text{Present} \rightarrow \text{Absent} \rightarrow \text{Present}$ (or repeated cycles).
  3. All periods satisfy `minimum_period_documents`.
- **Interpretation**: An intermittent topic that disappears from reporting and subsequently resurfaces.

### 5.7 `INSUFFICIENT_HISTORY`
- **Conditions**: Assigned whenever $K < 2$, total documents in a period $< \text{minimum\_period\_documents}$, or total topic documents $< \text{minimum\_topic\_documents}$.

---

## 6. Persistence Classifications

For tracking long-term presence across $M$ total periods in the analysis:
- **`PERSISTENT`**: Present in $\ge 75\%$ of observed periods ($M \ge 2$).
- **`INTERMITTENT`**: Present in multiple non-consecutive periods but $< 75\%$ of observed periods ($M \ge 3$).
- **`NEW`**: First detected in the latest observed period ($M \ge 2$).
- **`DISAPPEARED`**: Present in early periods but absent in the final observed period.
- **`INSUFFICIENT_HISTORY`**: Only 1 period observed ($M = 1$).

---

## 7. Operational Examples

### Example 1: Standard Growth
- **FY2023-24**: 20 topic docs / 100 total docs (20.0%)
- **FY2024-25**: 30 topic docs / 100 total docs (30.0%)
- **Checks**:
  - Both periods $\ge 5$ docs (100 docs) $\to$ Gate passed.
  - $\Delta_{\text{abs}} = +10$ docs.
  - $\Delta_{\text{pp}} = +10.0$ percentage points ($> +2.0$ pp).
  - $g_{\text{rel}} = +50.0\%$.
- **Result**: `GROWING`.

### Example 2: Small Sample Protection
- **FY2023-24**: 1 topic doc / 5 total docs (20.0%)
- **FY2024-25**: 2 topic docs / 5 total docs (40.0%)
- **Checks**:
  - `minimum_period_documents = 5` passed, but `minimum_topic_documents = 2` failed in Period A (1 < 2).
  - A shift of 1 single document changes share by 20 percentage points!
- **Result**: `INSUFFICIENT_HISTORY` (guarded against small-sample over-classification).

---

## 8. Limitations & Engineering Guardrails

1. **No Causal Inference**: The engine outputs factual descriptions (e.g. *"Topic share increased from 20.0% to 30.0%"*). It does not infer causes (e.g. *"increased due to regulatory compliance push"*).
2. **Corpus Dependency**: All shares are relative to the ingested corpus. If a subsidiary ingested 50 mining plans in FY2023-24 but only 10 in FY2024-25, sample size shifts must be checked using the reported denominators.
3. **Deterministic Idempotency**: Given identical topic assignments and metadata, trend classifications will produce identical results across runs.

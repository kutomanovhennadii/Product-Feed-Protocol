# Determinism and Golden Harness

This document outlines the determinism guarantees of the PFP runtime and explains how the system is tested to ensure byte-perfect reproducibility.

## 1. What "Deterministic Output" Means in PFP

In the context of the PFP runtime, **determinism** means that a given input payload processed with a specific mapping configuration and schema will always produce a **byte-for-byte identical output artifact**. 

This byte-equality is a critical contract for:
*   Caching and deduplication.
*   Preventing unnecessary delta updates in downstream systems.
*   Reliable integration testing and regression analysis.

If deterministic properties are properly maintained, executing the pipeline twice on the same dataset produces the exact same file hash.

## 2. Injectable Parameters (`generated_at`)

By default, an artifact execution attaches a dynamic timestamp (`generated_at`) representing the UTC time of generation. This is useful for audit logging and metadata tracking, but it inherently breaks byte-equality because every run happens at a distinct time, modifying the `ArtifactMetadata`.

To guarantee determinism for testing and strictly cached environments, the PFP runtime allows **injecting** deterministic temporal values. 

For instance, when calling `ArtifactProducer.produce(...)`, the `generated_at` parameter can be explicitly overridden:

```python
from datetime import datetime, timezone

# Inject static timestamp for deterministic outcome
static_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

artifact = producer.produce(
    payload_stream=my_stream,
    target="stripe",
    schema_version="1.0.0",
    generated_at=static_time
)
```
When `generated_at` is statically injected, the resulting artifact and its metadata remain perfectly immutable across executions.

## 3. The Golden Harness Guarantees

To enforce this determinism policy, PFP maintains a rigorous testing structure known as the **Golden Harness**. It is implemented across two distinct test layers in the underlying core repository (`tests/schema_matrix/` and `tests/e2e/`).

### `tests/matrix/`
The Matrix testing suite systematically checks permutations of the runtime components. It stores a suite of **Golden Files** (pre-approved, byte-ideal outputs). 
When tests run, they enforce determinism by:
1. Injecting static timestamps (`generated_at`).
2. Generating artifacts in-memory via combinations of adapters, matchers, and client mocks.
3. Comparing the generated payload bytes directly against the stored `.csv` or `.json` Golden Files using a strict diff.

### `tests/e2e/`
The E2E tests validate complete pipeline flows. They similarly inject deterministic bounds and verify that end-to-end processing (from raw input mock to published dummy-client chunk) yields outputs strictly equivalent to the E2E Golden outputs, ensuring no non-deterministic side-effects (such as unordered dictionary serialization or random log injections) pollute the payload stream.

### Commitment
By validating against the Golden Harness in Continuous Integration, the PFP project guarantees that its determinism promises are cryptographically secure and protected against unintended regressions.
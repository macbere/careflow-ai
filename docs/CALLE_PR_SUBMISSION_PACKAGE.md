# CALL-E Community Contribution

CareFlow's reusable community contribution is the **`structured-outcome-followup-call`** Agent Skill.

## Current status

The contribution was opened as CALL-E community **PR #268** and has been **merged** into the official
`CALLE-AI/awesome-phone-call-agents` repository:

https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268

## What the contribution contains

The skill generalizes CareFlow's provider-neutral pattern into a reusable non-healthcare example:

```text
goal-driven call
  -> structured outcome
  -> deterministic rubric
  -> conditional follow-up action
```

The contribution includes:

- `SKILL.md` describing the reusable workflow pattern.
- `scripts/mock_provider.py` for safe credential-free execution.
- `scripts/orchestrate_example.py` with a delivery-exception worked example.
- `assets/example_rubric.json` containing the deterministic example rubric.
- `references/result_schema_guide.md` for structured-result design.
- `references/safety_checklist.md` covering consent, idempotency, phone formatting, credentials,
  and boundaries against professional advice.

## Why it matters to CareFlow

CareFlow uses the same broader architecture in a healthcare follow-up prototype, while the
community skill deliberately removes healthcare-specific assumptions. This demonstrates that the
core CALL-E orchestration pattern is reusable outside the hackathon application itself.

The copy retained in this repository is under:

`calle-contrib/structured-outcome-followup-call/`

## Local verification

The contribution's deterministic example is covered by the repository test suite and can also be
run directly without live CALL-E credentials:

```bash
python calle-contrib/structured-outcome-followup-call/scripts/orchestrate_example.py
```

The merged upstream PR is the authoritative public record of the contribution's acceptance.

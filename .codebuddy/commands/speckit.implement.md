---
description: Run agent-native implement orchestration or execute one worker handoff.
---


<!-- Source: test-first-governance -->
# Test-First Implementation Wrapper

Apply these execution rules in addition to the core implementation workflow.

## Critical Execution Rules
- Do not write production code for a behavior slice until its required TDD and applicable ATDD/BDD executable evidence exists.
- Run the new evidence for the current slice before its production change and confirm it fails for the expected missing behavior. Record red-state evidence in task, PR, or CI output; write a persistent report only when the plan requires versioned retention.
- After the expected failure, update the artifact's Evidence Artifact Registry entry to `Red` with its evidence path.
- If a failure is unexpected, flaky, environment-caused, or product-breaking, create or update the corresponding `specs/<feature>/defect-log.md` entry instead of hiding it in task notes.
- Implement the smallest production change needed to pass the current slice's failing evidence.
- Rerun the slice evidence, update its registry entry to `Green`, and refactor while keeping the relevant suites green.
- Complete one Red-Green-Refactor cycle before adding executable evidence for the next slice; do not batch every failing test for the story before implementation.
- Run full TDD, all executable evidence mapped to required BDD/ATDD roles, coverage, linting, formatting, and every quality gate marked `Required` before marking the story complete.
- Update each executed artifact in the registry and each gate in Quality Gate Results to `Green` or `Blocked`; retain `N/A` only with its approved rationale and alternative evidence.
- Keep the Scenario Coverage Matrix current when scenarios, examples, sampling strategies, shared BDD/ATDD evidence, or source mappings change.
- Keep `defect-log.md` current for open, fixed, verified, rejected, and deferred defects.
- Keep `test-summary.md` current at story and feature completion with execution totals, coverage/traceability status, defect summary, risks/exceptions, evidence links, and Go/No-Go recommendation.
- Mark tasks `[X]` only after the relevant tests/gates have been executed and evidence paths exist.

## Failure Handling
If a test fails for an unexpected reason, stop the current story implementation and report:
- failing command;
- failing suite (`TDD`, `BDD`, `ATDD`, or gate);
- expected failure reason vs actual failure reason;
- file path and scenario/test ID;
- proposed fix;
- defect ID or rationale for not creating a defect entry.

## Input
```text
$ARGUMENTS
```
Optional runtime hint: `agent-runtime=<spec-kit-integration-key>`.
## Mode
- Core mode: no handoff JSON path in `$ARGUMENTS`.
- Worker mode: `.json` handoff path in `$ARGUMENTS` or `Use handoff JSON <path>`.
- Forbidden: external dispatch scripts, workflow runners, inline worker execution.
## Authority
- Core Agent is the orchestrator: build `context-index.json`, assemble `handoff-manifest.json`,
  dispatch isolated runs, review receipts, update `tasks.md` only during task commit,
  and run integration verification.
- Vertical Planner Agent is the capability planner: plan exactly one `vertical_capability`,
  produce shard plans plus handoff/context digest drafts, and never execute implementation
  or write the final manifest.
- Worker Agent is the handoff executor: execute exactly one handoff and never edit `tasks.md`,
  create handoffs, or dispatch workers.
## Core Agent
- Follow the lifecycle and runtime isolation contract in `tests/contracts/speckit-cross-agent-subagents.md`.
- Map planned `U` design objects to concrete source, test, fixture, configuration,
  and receipt paths before worker execution.
- Use `isolated_subagent` only when the runtime provides isolated subagent/subsession execution.
- Otherwise use manifest `execution_mode: manual_fresh_worker_session`.
- If isolation is unavailable or unknown, write the manifest and handoffs, then stop with Worker-mode instructions.
- Consume planner outputs and worker receipts, not worker conversation history.
## Vertical Planner Agent
- Read only `tasks.md`, `context-index.json`, and allowed planning artifacts.
- Preserve `tasks.md` order, lifecycle dependencies, capability boundaries, and Change Scope Granularity.
- Put unresolved shard, context, asset binding, or path ambiguity into `context_gaps`.
- Emit drafts that validate against the handoff schema before Core assembly.
## Worker Agent
- Reject non-existent handoff paths.
- Reject handoffs not listed in `handoff-manifest.json`.
- Verify `contract_type` is `speckit.implement.handoff.v2`.
- Load `context_digest_path` before editing.
- Stop before editing when `context_gaps` is not empty.
- Execute only `task_ids`.
- Read only `allowed_read_paths`.
- Write only `allowed_write_paths`.
- Write `task_status_update.receipt_path` as `speckit.implement.receipt.v1`.
- Do not edit `tasks.md`.
## Contract References
- Runtime, shard, context digest, path, asset binding, dispatch, Worker Prompt,
  and review receipt rules: `tests/contracts/speckit-cross-agent-subagents.md`.
- Manifest schema: `schemas/speckit.implement.manifest.v1.schema.json`.
- Handoff schema: `schemas/speckit.implement.handoff.v2.schema.json`.
- Receipt schema: `schemas/speckit.implement.receipt.v1.schema.json`.
- Cross-field validation: `validators/speckit_implement_contract.py`.
## Runtime Stops
- Stop on missing handoff files, unlisted handoffs, non-empty `context_gaps`, schema mismatch,
  write paths outside `allowed_write_paths`, or attempts to update planning artifacts from Worker mode.
- Stop instead of inventing validation strategy, adding lifecycle roles, changing requirements,
  updating contracts, widening scope, or adding standalone validation planning artifacts.


## Additional Done Criteria
- [ ] Reproducible red-state evidence exists in the retention location declared by the plan
- [ ] All TDD tests pass and approved coverage thresholds are met without baseline regression
- [ ] All scenarios mapped to required BDD roles pass and have executable bindings
- [ ] All scenarios mapped to required ATDD roles pass and have executable bindings
- [ ] The Scenario Coverage Matrix covers every required behavior, acceptance boundary, edge/error condition, and approved example or sampling strategy
- [ ] Shared BDD/ATDD evidence uses one owning-suite execution route, provides both mapped roles, and records an equivalence rationale
- [ ] Every BDD/ATDD `N/A` remains justified and has alternative evidence
- [ ] Linting/formatting has zero blocking findings
- [ ] Every required static-analysis, security, and runtime-smoke gate passes
- [ ] Every gate `N/A` and threshold exception remains justified and approved
- [ ] `specs/<feature>/test-traceability.md` has no missing source mappings, dangling artifact IDs, duplicated execution fields, or stale registry/gate statuses
- [ ] `specs/<feature>/defect-log.md` reflects all unexpected failures, open defects, deferred defects, accepted risks, and verification closures
- [ ] `specs/<feature>/test-summary.md` reflects final execution, coverage, traceability, defect, risk, evidence, and recommendation status
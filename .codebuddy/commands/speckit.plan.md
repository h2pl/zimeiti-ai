---
description: Wrap the core planning workflow with Phase 0 behavior projection and optional design artifacts.
scripts:
  sh: .specify/scripts/bash/setup-plan.sh --json
  ps: .specify/scripts/powershell/setup-plan.ps1 -Json
  py: .specify/scripts/python/setup_plan.py --json
---


<!-- Source: test-first-governance -->
# Test-First Planning Wrapper

Apply these requirements in addition to the core planning workflow.

## Mandatory Planning Outputs
The implementation plan MUST include:
- test directory structure with visible ownership for every applicable suite;
- selected tools and commands for TDD, BDD, ATDD, coverage, linting, formatting, static analysis/type checking, security, and runtime smoke validation;
- gate applicability, blocking behavior, risk-based thresholds, and exception policy;
- CI output or artifact locations and any explicit versioned-report retention requirement;
- red-green-refactor execution model for every user story;
- a materialized `specs/<feature>/test-traceability.md` with an evidence artifact registry, source-to-artifact coverage map, scenario coverage matrix, applicability decisions, and quality-gate results;
- a materialized `specs/<feature>/defect-log.md` for defect triage, release-impact decisions, accepted risks, and verification closure;
- a materialized `specs/<feature>/test-summary.md` for execution summary, coverage summary, defect summary, risks/exceptions, evidence links, and Go/No-Go recommendation;
- BDD and ATDD applicability decisions, including rationale and alternative evidence for every `N/A`.
- coverage-complete, non-duplicative scenario mappings showing how every `Required` BDD/ATDD role is satisfied, which suite owns each artifact, and which scenario/example rows cover each source.

## Minimum Professional Test Reports
Create and maintain the minimum professional reporting set for the feature:
- `plan.md` acts as the Test Plan: scope, strategy, tools, environments, gates, thresholds, and evidence-retention policy.
- `specs/<feature>/test-traceability.md` acts as the combined Test Inventory, Requirements Traceability Matrix, execution evidence index, scenario coverage matrix, and quality-gate results report.
- `specs/<feature>/defect-log.md` acts as the Defect Report: defects, unexpected failures, severity/priority, triage, risk acceptance, and verification closure.
- `specs/<feature>/test-summary.md` acts as the Test Summary Report: execution results, coverage/traceability status, defect status, risks/exceptions, evidence references, and release recommendation.

Do not create extra standalone reports unless the plan declares an audit, regulatory, customer, or tool-integration reason. CI artifacts and machine-readable runner outputs remain raw evidence referenced by these reports.

Project or release-level aggregation is handled later by `/speckit.converge` through a single overall Test Summary Report at `reports/test-summary.md` or `reports/releases/<release-id>/test-summary.md`. Do not create overall traceability, inventory, execution, or defect reports during feature planning unless an external requirement is declared.

Declare the destination decision before convergence:

| Setting | Value |
|---------|-------|
| Overall summary mode | [rolling/release] |
| Release ID | [N/A or release-id] |
| Output path | [reports/test-summary.md or reports/releases/<release-id>/test-summary.md] |
| Rationale | [why this destination is appropriate] |

Use `rolling` with `reports/test-summary.md` when the project wants one latest aggregate report. Use `release` with `reports/releases/<release-id>/test-summary.md` when the project wants versioned release evidence. If no release ID is provided, default to `rolling`.

## Mandatory Report Creation
Before reporting planning complete:
1. Resolve `test-traceability-template` through Spec Kit's template resolver (for example, `specify preset resolve test-traceability-template`).
2. Resolve `defect-log-template` and `test-summary-template` through Spec Kit's template resolver.
3. Materialize the resolved templates at `specs/<feature>/test-traceability.md`, `specs/<feature>/defect-log.md`, and `specs/<feature>/test-summary.md`.
4. Populate the Evidence Artifact Registry with planned artifact IDs, owning suites, evidence roles, paths, and commands.
5. Populate the Source Coverage Map with all known source IDs and their artifact IDs.
6. Populate the Scenario Coverage Matrix with scenario/example rows, primary source IDs, input classes, interfaces, and sampling or shared-evidence rationales.
7. Populate applicability decisions and Quality Gate Results without duplicating mutable artifact execution fields in source mappings.
8. Initialize `defect-log.md` with zero known defects or known planning defects, severity/priority policy, and release-impact review placeholders.
9. Initialize `test-summary.md` with report references, planned scope, planned evidence locations, and `Blocked` or `Not Run` status; do not claim Pass or Go during planning.
10. Set unexecuted required evidence to `Planned`; do not claim Red, Green, Pass, or Go results during planning.

If these report artifacts already exist, update them in place and preserve valid execution history, defect history, risk-acceptance decisions, approvals, and evidence links.

## Tool Selection Guidance
Choose stack-native tools. Examples:
- Python: pytest, pytest-bdd/behave, coverage.py, ruff, mypy/pyright, bandit where applicable.
- TypeScript/JavaScript: Vitest/Jest, Cucumber.js/Playwright, c8/nyc, ESLint, TypeScript compiler, dependency audit where applicable.
- Java: JUnit, Cucumber JVM, JaCoCo, Checkstyle/SpotBugs/Error Prone where applicable.
- .NET: xUnit/NUnit/MSTest, SpecFlow/Reqnroll, Coverlet, dotnet format, analyzers.
- Go: go test, godog, coverage, go vet, staticcheck.


## Change Scope Granularity

Apply the constitution's Change Scope Granularity principle.

During planning, lock the change scope to `M + U`: module/capability plus design object. Do not lock operation-level implementation details or concrete write paths.

## Design Artifact Policy

Core planning remains authoritative. Optional design artifacts carry structured details that do not belong in `plan.md`.

Generate design artifacts only when the feature requires internal object design or cross-boundary sequence constraints:

- `class-diagram.md`: internal implementation object structure.
- `contracts/sequences.md`: service-call, command, event, and integration sequencing.

For simple features, keep artifacts concise. `N/A` sections require a concrete rationale, for example "No service boundary exists for this static documentation change." Do not create large placeholder files.

Keep `plan.md` as summary/navigation. It must link generated design artifacts and must not embed complete class diagrams or complete sequence diagrams.

Store service sequences only at `contracts/sequences.md`, even when there are no other contract files. Do not create a root-level `sequences.md`.

Validation strategy is not a standalone planning artifact. Planning-time validation decisions belong in `research.md`; executable validation paths belong in `quickstart.md`; concrete test and verification tasks belong in `tasks.md` through the tasks command.

## Phase 0 Preflight

Before core research or design work, verify checklists/behavior-testability.md has passed: it must have `Gate Status: PASS` and `Blocking Items: none` or a `Blocking Items` section containing only `- none`.

If the checklist is missing, incomplete, has `Gate Status: BLOCKED`, or lists blocking items, stop with a report-only/no-write failure before planning artifacts are generated. Report an upstream gate failure with the missing checklist item or readiness gap. Do not create or update feature files, and must not create or update behavior artifacts. Return to `/speckit.checklist` or `/speckit.clarify` instead of repairing requirements inside planning.

Phase 0 preflight must not modify `spec.md`, ask clarification questions, create formal contracts, or bypass the checklist gate.

## Phase 0 Behavior Projection

After Phase 0 preflight passes and before core research or design work, project the accepted `spec.md` requirements into behavior drafts:

- `behavior/bdd.draft.feature`: readable BDD draft scenarios.
- `behavior/behavior-scenarios.draft.json`: structured draft scenario IDs, Given inputs, When actions, Then outcomes, and source.
- `behavior/uif.intent.json`: interaction intent extracted from accepted requirements.
- `behavior/data-fixtures.intent.json`: data setup intent required by draft scenarios.

Required case types from `checklists/behavior-testability.md` must project into `behavior/behavior-scenarios.draft.json`. Do not continue with only positive scenarios when Required case types exist. If a Required case type cannot be projected without inventing requirements, stop with a report-only/no-write failure and return to `/speckit.checklist` or `/speckit.clarify`.

Phase 0 behavior projection is a projection step, not a new requirement-discovery step:

- Do not discover new requirement problems.
- Do not ask clarification questions.
- Do not modify `spec.md`.
- Do not generate formal contracts.
- Do not decide test level, fixture strategy, external-system strategy, interface design, or validation commands.

Structured JSON draft artifacts must follow their matching `schemas/speckit.behavior.*.schema.json` contracts.

If Phase 0 cannot generate behavior drafts from a `spec.md` that passed checklist, stop with a report-only/no-write failure. Do not create or update partial behavior artifacts. The remedy is to return to `/speckit.checklist` or `/speckit.clarify`; do not invent missing requirements during planning.

## Additional Phase 1 Design Outputs

During Phase 1, after Phase 0 behavior projection and core research have resolved planning unknowns and while producing design/contracts, create or update these artifacts only when their trigger conditions are met:

1. `class-diagram.md`
   - Capture key classes, interfaces, abstract types, services, repositories, adapters, factories, strategies, controllers, and coordinators.
   - Explain each core type's responsibility and the relationships that constrain implementation: inheritance, composition, aggregation, dependency, and references.
   - Format must be Mermaid, PlantUML, or structured table; selected format must expose type responsibilities and relationships.
   - Do not define API request/response fields, domain business fields, test cases, task IDs, private helpers, or method-level implementation details.

2. `contracts/sequences.md`
   - Capture the observable flow of API requests, commands, events, callbacks, async workers, external systems, retries, compensation, rollback, and failure branches.
   - Include participants, service boundaries, main success paths, important alternate paths, and failure handling that affects implementation or testing.
   - Format must be Mermaid sequence diagram or structured text; selected format must expose participants, boundaries, success paths, and failure paths.
   - Do not define field schemas, internal class inheritance, test matrices, or user-facing run instructions.

When `plan.md` has a design artifact/navigation section, include links to:

- Internal object design: `./class-diagram.md`
- Service sequences: `./contracts/sequences.md`
- Behavior draft: `./behavior/bdd.draft.feature`
- BDD contracts: `./contracts/bdd/`
- Expected UIF contracts: `./contracts/uif/`
- Behavior contracts: `./contracts/behavior/`
- Data model: `./data-model.md`
- Interface contracts: `./contracts/`
- Validation path: `./quickstart.md`

When visual requirements are in scope, keep `plan.md` navigation linked to visual fidelity scope, screenshot refs, visual proof refs, and Design Requirement trace refs already accepted by `spec.md` and the readiness checklist.

## Visual Planning Responsibilities

When visual requirements are in scope, planning must keep the Visual Fidelity Evidence Matrix as the upstream readiness record and split visual carry-forward across the existing planning outputs:

- `research.md`: add Visual validation decisions for each relevant Visual Item ID. Record selected test level, fixture or asset strategy, viewport/state coverage strategy, visual regression or baseline proof strategy, screenshot refs, visual proof refs, Design Requirement trace refs, related quickstart validation path, and related UIF or behavior contract path. Do not copy the Visual Fidelity Evidence Matrix into `research.md`, do not create new visual requirements, do not call Figma or other provider tools, and do not rebuild provider evidence matrices.
- `contracts/uif/` and `contracts/behavior/`: formalize accepted visual interaction and state constraints only when they affect observable behavior. Expected UIF contracts may carry visual_item_refs, viewport_matrix_refs, state_matrix_refs, visual_proof_refs, and accepted_exception_refs. Behavior contracts may reference visual assertion IDs or blockers when a visual state cannot be formalized without inventing requirements. Interface contracts in `contracts/` may model only API or data fields needed to support UI states, assets, or feedback; they must not contain layout rules or screenshot proof decisions.
- `contracts/sequences.md`: add UI interaction sequence, visual state handoff points, responsive branch trigger refs, and visual proof references only when visual states affect cross-boundary order, async callbacks, retries, rollback, compensation, or error propagation. Keep visual style, tokens, layout breakpoints, screenshot matrices, and validation commands out of `contracts/sequences.md`.

## Behavior-First Planning Inputs

Use the Phase 0 behavior projection drafts as planning inputs:

- `behavior/bdd.draft.feature`
- `behavior/behavior-scenarios.draft.json`
- `behavior/uif.intent.json`
- `behavior/data-fixtures.intent.json`

Phase 1 outputs must cite applicable draft scenario IDs or record `N/A or blocker`.

During Phase 1, if behavior drafts exist and checklists/behavior-testability.md has passed, you must formalize them into formal behavior contracts:

- `contracts/bdd/`: acceptance-level BDD contracts.
- `contracts/uif/`: Expected UIF contracts.
- `contracts/behavior/`: scenario instance, fixture, and assertion contracts.

Required case types from `checklists/behavior-testability.md` must formalize into `contracts/behavior/scenario-instances.json`. Do not continue with only positive scenarios when Required case types exist. Map each Required Case ID to a Scenario ID or `case_coverage_blockers` entry. When a Required case type cannot be formalized, write `case_coverage_blockers` in `contracts/behavior/scenario-instances.json` and record `N/A or blocker` with the Case ID, missing planning input, and downstream contract path.

When formalizing BDD Draft into `contracts/bdd/*.feature`:

- Preserve scenario intent and business outcome from the draft.
- Convert ambiguous Given steps into formal fixture, actor, state, permission, or start-view conditions.
- Convert When steps into formal user events, request cases, or system triggers aligned with UIF/API contracts.
- Convert Then steps into formal feedback, response, business state, or assertion expectations.
- If a step cannot be formalized without inventing information, record `N/A or blocker` instead of guessing.
- Do not introduce independent traceability mechanisms for BDD formalization.

If behavior drafts exist but cannot be formalized, write `N/A or blocker` in the affected planning artifact with the source draft path, the missing planning input, and the downstream contract path that could not be produced. Do not silently skip behavior draft formalization.

BDD draft reasoning must feed the normal planning outputs:

- `research.md`: record the selected test level, fixture strategy, mock/external-system strategy, and error-branch validation decisions for each behavior scenario type that affects implementation.
- `data-model.md`: model formal behavior entities referenced by behavior contracts, including `BehaviorScenarioInstance`, `DataFixture`, `UIFPath`, `FeedbackView`, and `BehaviorAssertion`.
- `contracts/`: align interface contracts with BDD When steps, Expected UIF `api_call` steps, and behavior assertions.
- `quickstart.md`: include validation paths that exercise the formal BDD/UIF/behavior contracts.

Keep `plan.md` as summary/navigation for these formal behavior contracts. Product requirements stay in `spec.md`, domain details stay in `data-model.md`, interface schemas stay in `contracts/`, and validation run guidance stays in `quickstart.md`.


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before planning)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_plan` key
- If the YAML cannot be parsed or is invalid, do not skip silently: tell the user that `.specify/extensions.yml` could not be read (include the parser error) and that no hooks were checked, including any mandatory (`optional: false`) hooks registered there, then continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

1. **Setup**: Run `.specify/scripts/powershell/setup-plan.ps1 -Json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, FEATURE_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Re-evaluate Constitution Check post-design

## Mandatory Post-Execution Hooks

**You MUST complete this section before reporting completion to the user.**

Check if `.specify/extensions.yml` exists in the project root.
- If it does not exist, or no hooks are registered under `hooks.after_plan`, skip to the Completion Report.
- If it exists, read it and look for entries under the `hooks.after_plan` key.
- If the YAML cannot be parsed or is invalid, do not skip silently: tell the user that `.specify/extensions.yml` could not be read (include the parser error) and that no hooks were checked, including any mandatory (`optional: false`) hooks registered there, then continue to the Completion Report.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Mandatory hook** (`optional: false`) — **You MUST emit `EXECUTE_COMMAND:` for each mandatory hook**:
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook.
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

## Completion Report

Command ends after Phase 1 design. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Define interface contracts** (if project has external interfaces) → `/contracts/`:
   - Identify what interfaces the project exposes to users or other systems
   - Document the contract format appropriate for the project type
   - Examples: public APIs for libraries, command schemas for CLI tools, endpoints for web services, grammars for parsers, UI contracts for applications
   - Skip if project is purely internal (build scripts, one-off tools, etc.)

3. **Create quickstart validation guide** → `quickstart.md`:
   - Document runnable validation scenarios that prove the feature works end-to-end
   - Include prerequisites, setup commands, test/run commands, and expected outcomes
   - Use links or references to contracts and data model details instead of duplicating them
   - Do not include full implementation code, model/service/controller bodies, migrations, or complete test suites
   - Keep this artifact as a validation/run guide; implementation details belong in `tasks.md` and the implementation phase

**Output**: data-model.md, /contracts/*, quickstart.md

## Key rules

- Use absolute paths for filesystem operations; use project-relative paths for references in documentation
- ERROR on gate failures or unresolved clarifications

## Done When

- [ ] Plan workflow executed and design artifacts generated
- [ ] Extension hooks dispatched or skipped according to the rules in Mandatory Post-Execution Hooks above
- [ ] Completion reported to user with branch, plan path, and generated artifacts


## Design Artifact Reporting

Before finishing, the final report must list generated artifacts and state whether each is populated or intentionally minimal:

- `class-diagram.md`: populated, intentionally minimal, or not applicable with reason.
- `contracts/sequences.md`: populated, intentionally minimal, or not applicable with reason.

Also report where validation decisions were recorded:

- `research.md`: selected test level, fixture strategy, mock/external-system strategy, and error-branch validation decisions required by behavior contracts.
- `quickstart.md`: executable validation paths for the planned behavior contracts.

Report unresolved design gaps separately from downstream tasks. Do not mark the planning run complete if a design artifact contains unresolved `NEEDS CLARIFICATION` items that block task generation.


## Additional Planning Gate
Before completing the plan, verify:
- [ ] The plan makes tests mandatory, not optional
- [ ] Every required BDD and ATDD evidence role maps to an executable binding and owning-suite command
- [ ] The Scenario Coverage Matrix covers every required BDD/ATDD behavior, acceptance boundary, edge/error condition, and required example class
- [ ] Every scenario outline enumerates required examples or records an approved sampling strategy
- [ ] Shared BDD/ATDD evidence has one owning suite and one execution path, with both roles recorded in traceability
- [ ] Shared BDD/ATDD evidence records why behavior and acceptance intent are equivalent
- [ ] Every BDD/ATDD `N/A` remains justified and is not contradicted by the planned behavior
- [ ] Coverage thresholds protect changed code and the accepted project baseline
- [ ] Every gate has a command or a justified `N/A`, plus blocking behavior and evidence retention
- [ ] Lower threshold exceptions identify scope, rationale, compensating evidence, approver, and expiry/follow-up
- [ ] `specs/<feature>/test-traceability.md` contains complete registry, coverage-map, scenario-matrix, applicability, and gate sections with no duplicated execution state
- [ ] `specs/<feature>/defect-log.md` exists, uses the defect-log template sections, and is initialized for known defects or zero known defects
- [ ] `specs/<feature>/test-summary.md` exists, uses the test-summary template sections, links the plan/traceability/defect reports, and remains non-final until execution evidence exists
- [ ] The plan declares the Overall Test Summary Destination decision or states that convergence will default to `rolling` at `reports/test-summary.md`
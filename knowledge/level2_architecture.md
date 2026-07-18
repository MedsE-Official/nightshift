# Nightshift Level 2 Architecture

Level 2 introduces human-governed, role-specific execution.

## Runtime flow

1. Planner selects one work block using its configured role profile.
2. Librarian creates a deterministic repository map.
3. Architect produces a structured `ArchitectureContract`.
4. The contract is persisted before any code is changed.
5. With `architecture_approval_policy: file`, execution stops until a matching
   `architecture_approval.json` is supplied.
6. Builder receives only the approved contract and its allowed files.
7. Deterministic verification runs without AI.
8. Reviewer receives the original requirement, contract, diff and test output,
   but not the Builder conversation.
9. Historian writes a retrospective linked to feature, task, cycle, Git commit
   and Nightshift version.

## Approval file

For a pending contract, create `architecture_approval.json` beside the contract:

```json
{
  "contract_id": "the-id-from-architecture_contract.json",
  "decision": "approved",
  "comment": "Reviewed and approved"
}
```

Valid decisions are `approved`, `rejected`, and `pending`.

## Role configuration

Roles are configured under `roles` in `config.json`. Orchestration selects a
role; `ModelRegistry`, `ModelManager`, and `RoleRunner` resolve and prepare the
model. The workflow therefore does not depend on one specific model.

## Artifacts

Each cycle is stored under:

`history/<feature>/<task>/<cycle>/`

The folder includes identity, planner output, repository map, architecture
contract, approval, Builder attempts, verification, review and retrospective.

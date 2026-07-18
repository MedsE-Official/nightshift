# Nightshift role contracts

Nightshift is organized as a chain of narrow roles. Each role may make decisions
only inside its own responsibility and must treat the previous handoff as a
contract.

## Planner

The Planner selects one small, independently verifiable work block. It defines
scope and candidate files, but does not design the implementation or write code.

## Architect

The Architect resolves design ambiguity for exactly one Planner block and emits
an immutable `ArchitectureContract` containing:

- goal and summary;
- allowed and forbidden files;
- required implementation changes;
- APIs to preserve or intentionally remove;
- risks;
- objective acceptance criteria.

The Architect may narrow the Planner's file scope, but may not silently expand
it. It does not write code.

## Builder

The Builder implements the architecture contract exactly. It receives only the
files listed in `allowed_files`. It must not redesign the solution, add product
requirements, or modify files outside the contract. Contradictory or incomplete
contracts should be reported rather than guessed around.

## Reviewer

The Reviewer checks the implementation against the same architecture contract.
It does not redesign or implement. Approval requires deterministic verification,
no protected-path violations, no architecture-scope violations, and evidence for
every acceptance criterion.

## Test and verification

Verification executes configured commands and Git diff checks. Deterministic
failures override model opinions.

## Handoff invariant

A role must not solve decisions owned by an earlier role. Missing information is
a failed handoff, not permission to invent requirements.

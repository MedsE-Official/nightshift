# Nightshift Architecture & Vision

Version: Living Document

# 1. Vision

Nightshift is not an AI coding assistant.

Nightshift is an AI software engineering organization.

Its purpose is to autonomously evolve external software projects while
keeping humans responsible for product vision and major architectural
decisions.

...

# Executive Summary

Nightshift separates *thinking* from *doing*.

The Human decides **what** should exist.

The Architect decides **how the product should evolve**.

The Planner decides **what should happen next**.

The Builder writes code.

The Reviewer validates quality.

Nothing skips these responsibilities.

# 2. Product Philosophy

## Human remains Product Owner

Humans describe intent.

This intent lives in:

    .nightshift/requirements.md

This document is the only human-authored product specification.

Everything else can be regenerated.

## Framework vs Project

Nightshift itself contains generic orchestration logic.

Every target repository contains:

``` text
project/
    .nightshift/
        project.json
        backlog.json
        knowledge.json
        requirements.md
```

This separation allows one Nightshift installation to develop many
independent repositories.

# 3. Agent Responsibilities

## Human

Owns: - Product vision - Business priorities - Acceptance -
Architectural direction

Never manually edits backlog tasks unless desired.

## Architect

Never edits code.

Responsibilities:

-   Read requirements.md
-   Read knowledge.json
-   Read backlog.json
-   Analyze repository
-   Detect completed work
-   Detect missing work
-   Create Features
-   Create Tasks
-   Prioritize work
-   Prevent duplicates
-   Detect obsolete tasks
-   Keep backlog synchronized

Architect thinks in months.

## Planner

Planner never invents functionality.

Planner:

-   chooses next executable task
-   respects dependencies
-   skips completed work
-   finishes tasks
-   hands work to Builder

Planner thinks in hours.

## Builder

Builder implements exactly one task.

Builder must never redesign architecture.

## Reviewer

Reviewer decides whether implementation satisfies:

-   requirements
-   task
-   quality
-   tests

Reviewer can reject work.

# 4. Information Flow

    Human
        │
    requirements.md
        │
    Architect
        │
    Features
        │
    Planner
        │
    Task
        │
    Builder
        │
    Tests
        │
    Reviewer
        │
    Task Complete

# 5. requirements.md

The decision to use requirements.md instead of requirements.txt was
deliberate.

Reasons:

-   avoids conflict with Python dependency management
-   supports Markdown
-   supports diagrams
-   supports long-form documentation
-   is clearly human-authored

requirements.md becomes the canonical product definition.

# 6. Backlog

Current model

``` json
{
  "schema_version":"1.0",
  "features":[
    {
      "id":"calculator-v1",
      "title":"Calculator",
      "tasks":[]
    }
  ]
}
```

Future feature metadata:

-   description
-   priority
-   status
-   created_at
-   updated_at

Planner owns tasks.

Architect owns features.

# 7. Initial Project Bootstrap

Minimal project:

-   project.json
-   knowledge.json
-   backlog.json
-   requirements.md

An empty backlog is acceptable.

Architect should generate the first feature hierarchy.

# 8. Development Cycle

1 Architect updates backlog

2 Planner selects task

3 Builder implements

4 Tests execute

5 Reviewer validates

6 Task completed

Repeat.

# 9. Design Principles

-   deterministic
-   explainable
-   reproducible
-   repository independent
-   model independent
-   review driven
-   test first
-   human supervised

# 10. Long-term Vision

Potential future capabilities:

-   dependency graphs
-   effort estimation
-   roadmap generation
-   automatic reprioritization
-   ADR generation
-   architecture health reports
-   portfolio management
-   multiple architect strategies
-   specialized builders
-   specialized reviewers
-   security reviewers
-   performance reviewers

Nightshift should become an autonomous engineering organization rather
than a coding assistant.

# 11. Architectural Decisions

-   JSON for machine editable state.
-   Markdown for human editable knowledge.
-   External repositories only.
-   Framework and project knowledge separated.
-   Architect owns evolution.
-   Planner owns execution.
-   Builder owns implementation.
-   Reviewer owns quality.

# 12. Open Questions

-   Feature dependency model
-   Cross-project knowledge
-   Multi-architect collaboration
-   Long-term memory
-   Automatic refactoring campaigns
-   Continuous architecture reviews

# 13. Living Document

Every significant architectural decision should be documented before
implementation whenever practical.

The architecture should evolve intentionally rather than accidentally.

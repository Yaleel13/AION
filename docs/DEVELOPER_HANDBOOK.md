# AION Developer Handbook

## Purpose

This handbook protects architectural coherence as AION evolves from specifications into a working platform.

## Repository Principles

- Constitution before convenience.
- Evidence before claims.
- Explicit schemas before implicit behavior.
- Small, reviewable changes before broad rewrites.
- Tests for behavior, not only implementation details.
- Documentation changes accompany architectural changes.
- Secrets, credentials, and private user data never enter the repository.

## Branch and Pull Request Standards

- Use focused branches named by outcome.
- Keep pull requests scoped to one coherent milestone.
- Describe what changed, why it changed, user impact, risks, and validation.
- Default to draft pull requests for substantial architectural work.
- Avoid mixing unrelated refactors and features.

## Documentation Standards

Canonical specifications live in:

- `constitution/`
- `identity/`
- `core/`
- `protocols/`
- `agents/`
- `docs/`

Documents that alter system-wide behavior must include a version note or changelog entry once versioning is introduced.

## Engineering Standards

- Use typed models for durable data.
- Preserve provenance, confidence, privacy classification, and timestamps.
- Separate provider integrations from domain logic.
- Keep orchestration, memory, knowledge, and agent behavior modular.
- Fail transparently and never report unverified completion.
- Prefer dependency injection and testable service boundaries.
- Log operational events without exposing sensitive content.

## Testing Philosophy

Tests should cover:

- constitutional and epistemic invariants;
- routing to appropriate agents;
- memory promotion and correction rules;
- knowledge graph validation;
- protocol outputs;
- provider failures and fallbacks;
- authentication and authorization;
- privacy and data deletion behavior;
- API contracts;
- regression paths.

## Definition of Done

A change is complete only when:

1. implementation and documentation agree;
2. relevant tests pass;
3. security and privacy impacts are considered;
4. migrations or manual steps are documented;
5. claims of working behavior are supported by validation;
6. the change preserves constitutional priorities.

## Contribution Review Questions

- Does this strengthen human agency?
- Is uncertainty represented honestly?
- Is durable data traceable to a source?
- Does the design minimize sensitive data?
- Is the behavior testable?
- Does this belong in AION's core, an agent, a protocol, or an integration?
- What could fail, and how will the system communicate that failure?
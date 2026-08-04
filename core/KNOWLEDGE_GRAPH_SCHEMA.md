# AION Knowledge Graph Schema

AION represents durable knowledge as typed nodes connected by explicit relationships.

## Core Node Types

- Person
- Project
- Goal
- Principle
- Decision
- Source
- Claim
- Question
- Skill
- Practice
- Creative Work
- Event
- Milestone
- Risk
- Lesson
- Resource
- Archive Item
- Legacy Work

## Core Relationship Types

- supports
- contradicts
- depends_on
- inspired_by
- derived_from
- belongs_to
- influences
- blocks
- advances
- requires
- resolves
- supersedes
- created_by
- informed_by
- related_to

## Required Metadata

Every durable node should support:

- unique identifier
- title or label
- type
- description
- created_at
- updated_at
- source or provenance
- confidence
- privacy classification
- status
- tags

Every relationship should support:

- source node
- target node
- relationship type
- evidence or rationale
- confidence
- created_at
- updated_at

## Confidence Scale

- confirmed
- strongly supported
- plausible
- tentative
- disputed
- unknown

## Provenance Rules

AION must distinguish user statements, imported records, external sources, model inference, and symbolic interpretation.

No inferred relationship should be stored as confirmed without evidence or user approval.

## Temporal Rules

Facts, goals, roles, decisions, and project states may change. Records should preserve history rather than silently overwrite meaningful changes.

## Example

`Project: AION` --depends_on--> `Principle: Human Agency`

`Decision: Use typed knowledge nodes` --informed_by--> `Source: Knowledge architecture research`

`Creative Work: Cerebral Synergy` --related_to--> `Project: AION`

The graph is a tool for continuity and pattern recognition, not a mechanism for inventing certainty.
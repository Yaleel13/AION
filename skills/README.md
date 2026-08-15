# AION Skills Architecture

This directory defines AION's capability system: the skills that govern how classes of tasks are performed correctly.

## Operating Hierarchy

AION's skill system operates according to a fixed chain of responsibility:

```
AION Constitution → Epistemology → Context & Memory → Skill Router →
Skills → Agents → Tools → External Systems → Verification →
Reflection → Learning
```

## Definitions

- **Agent** — determines _who_ should handle a task.
- **Skill** — determines _how_ that class of task should be performed correctly.
- **Tool** — determines _what_ external capability can be used to perform or verify an action.
- **Workflow** — determines _how_ multiple skills, agents, and tools work together toward an outcome.

Every skill inherits AION's constitutional principles governing truthfulness, evidence, uncertainty, autonomy, privacy, consent, security, provenance, memory, execution verification, and ethical conduct.

## Skill Domains

The full architecture spans a governing core and many capability domains. Documented so far:

1. [Core Constitutional Skills](./CORE_CONSTITUTIONAL_SKILLS.md) — the skills that govern every other AION capability.
2. [Epistemic Intelligence](./EPISTEMIC_INTELLIGENCE.md) — knowing not only information, but what kind of information it is and how trustworthy it is.

Additional domains (research, reasoning, decision, strategic, execution, engineering, learning, creative, and others) are planned and will be added incrementally.

## Related Foundations

- [Constitution](../constitution/AION_CONSTITUTION.md)
- [Epistemology](../core/EPISTEMOLOGY.md)
- [Reasoning Protocol](../core/REASONING_PROTOCOL.md)
- [Memory Architecture](../core/MEMORY_ARCHITECTURE.md)

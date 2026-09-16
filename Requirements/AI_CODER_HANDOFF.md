# AI Coding Agent Handoff

## Paste-ready master prompt

Use the following prompt with Codex or Claude Code after placing this requirements pack in the repository:

---

You are the lead engineer for the GiftFind RedisVL Search Demo.

Read these files completely before making changes:

1. `README.md`
2. `PRODUCT_REQUIREMENTS.md`
3. `TECHNICAL_SPEC.md`
4. `BUILD_PLAN_AND_ACCEPTANCE.md`

Build the application described in those documents. Treat them as authoritative. When they conflict, use this priority:

1. Security and data-safety requirements
2. Acceptance criteria
3. Technical specification
4. Product requirements
5. Recommended implementation details

Implementation principles:

- Use RedisVL directly for index lifecycle, queries and filters, vectorization, SemanticRouter, and re-ranking wherever supported by the chosen stable RedisVL version.
- The default demo must work entirely locally without paid API keys.
- Use a local sentence-transformer for embeddings and a RedisVL Hugging Face cross-encoder re-ranker.
- Keep relevance, personalization, and merchandising as separate stages.
- Preserve exact-brand protection and tenant eligibility as hard constraints.
- Implement graceful fallback from re-ranked to hybrid to lexical search.
- Never fake latency with sleeps and never label a baseline as OpenSearch unless OpenSearch is actually running and measured.
- Do not scrape Giftcards.com or use real customer data.
- Keep Docker Compose startup and all documented commands working after each milestone.

Workflow:

1. Inspect the repository and report any existing code or constraints that affect the plan.
2. Produce a concise milestone plan mapped to `BUILD_PLAN_AND_ACCEPTANCE.md`.
3. Implement one vertical milestone at a time.
4. After each milestone, run formatting, linting, type checks, unit tests, integration tests, and the relevant smoke test.
5. Fix failures before proceeding.
6. Update README instructions and an implementation-status checklist as the project evolves.
7. Record material technical decisions in `docs/decisions/` as short ADRs.
8. At completion, run the full test suite, golden-query evaluation, and a warm-model smoke/load test.

Do not stop at scaffolding. Do not leave required functionality as TODOs or mocks. Test doubles are acceptable only for controlled failure tests or optional external providers. If a requirement cannot be implemented with the installed stable RedisVL API, document the exact incompatibility, implement the smallest compatible fallback, and preserve the public behavior.

Begin by reading the requirements and inspecting the repository. Then present the milestone plan before editing.

---

## Suggested Codex invocation

Place the requirements in the repository root or `docs/requirements/`, then tell Codex:

> Implement this project using `AI_CODER_HANDOFF.md` as the execution prompt. Work milestone by milestone, run the required verification after every milestone, and continue until the definition of done is satisfied or you encounter a decision that materially changes scope, security, or architecture.

For a mature repository, first ask Codex to inspect existing conventions and reconcile the proposed package structure with the current codebase.

## Suggested Claude Code invocation

Place the requirements in the repository, then tell Claude Code:

> Read `AI_CODER_HANDOFF.md` and all referenced requirements. Create a milestone plan, then implement the complete demo. Maintain a checklist, verify each vertical slice, and do not claim completion until the full acceptance suite passes.

If desired, copy the durable project rules from the master prompt into the repository's `CLAUDE.md` while keeping product requirements in the four source documents.

## Decisions the coder may make autonomously

- Exact stable package patch versions.
- UI component library and visual theme.
- JSON versus Hash storage if the choice is justified and all index requirements are met.
- Locust versus k6.
- Prometheus versus an equivalent lightweight metrics endpoint.
- FLAT versus HNSW default, provided the corpus-size reasoning is documented.

## Decisions that require user confirmation

- Adding a required paid service or API.
- Replacing RedisVL with another framework.
- Removing comparison mode, SemanticRouter, re-ranking, exact-match protection, multi-tenancy, or evaluation.
- Introducing real BHN/customer data.
- Adding authentication, payment, or PCI scope.
- Materially changing the prescribed architecture or definition of done.

## Expected final handoff from the coder

The coding agent must provide:

- a concise architecture summary;
- exact startup, seed, test, and evaluation commands;
- active RedisVL and model versions;
- a table of completed acceptance criteria;
- known limitations;
- measured local latency with hardware/context clearly stated; and
- the recommended next step for deploying against Redis Cloud or Redis Enterprise.


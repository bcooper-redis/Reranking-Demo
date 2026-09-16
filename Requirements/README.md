# BHN RedisVL Search Demo — Requirements Pack

This pack is intended to be handed directly to an AI coding agent such as Codex or Claude Code. It defines a production-shaped demonstration of a gift-card discovery platform built on Redis and RedisVL.

## Business objective

Demonstrate that Redis is more than a faster replacement for OpenSearch. The application must show how Redis and RedisVL provide a reusable relevance platform for:

- fast gift-card retrieval;
- hybrid lexical and semantic search;
- neural re-ranking;
- unified routing across product search, support, balance, activation, and order-status intents;
- bounded personalization and merchandising;
- multi-tenant enterprise storefronts; and
- measurable improvements in latency and result quality.

The demo should tell a clear progression:

1. Baseline search is slow and often poorly ranked.
2. Redis hybrid retrieval is fast and has higher recall.
3. RedisVL re-ranking improves the order of results.
4. Redis-hosted profile and merchandising signals personalize results without defeating relevance.
5. The same platform can serve many enterprise storefronts.

## Documents

1. `PRODUCT_REQUIREMENTS.md` — personas, user stories, UX, scope, and success metrics.
2. `TECHNICAL_SPEC.md` — architecture, Redis schema, RedisVL usage, APIs, scoring, configuration, and operational constraints.
3. `BUILD_PLAN_AND_ACCEPTANCE.md` — phased implementation, testing, acceptance criteria, and demo script.
4. `AI_CODER_HANDOFF.md` — paste-ready master prompt and working rules for an autonomous coding agent.

## Required implementation posture

- RedisVL is the default Python application framework for indexes, query construction, vectorization, semantic routing, and re-ranking.
- Redis is the system of record for demo catalog documents, embeddings, profiles, real-time ranking features, and search telemetry.
- A local embedding model and local cross-encoder must work without third-party API keys.
- Optional Cohere and VoyageAI re-ranker adapters may be enabled through environment variables.
- The app must run locally with one command using Docker Compose.
- The demo must not require payment, checkout, authentication, PCI data, or real customer data.

## Recommended stack

- Backend: Python 3.12+, FastAPI, Pydantic, RedisVL, redis-py.
- Frontend: React, TypeScript, Vite, accessible component primitives, and a lightweight charting library only if needed.
- Data store and search: Redis 8.4+ locally; configurable Redis Cloud/Redis Enterprise endpoint for hosted demonstrations.
- Local embeddings: `sentence-transformers/all-MiniLM-L6-v2` or a compatible small model.
- Local re-ranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` through RedisVL.
- Testing: pytest, Vitest, Playwright, and Locust or k6.

The coder may substitute equivalent current package versions but must preserve the architecture and acceptance criteria.


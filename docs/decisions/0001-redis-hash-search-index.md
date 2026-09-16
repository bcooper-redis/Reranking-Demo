# ADR 0001: Store Gift Cards as Redis Hashes for the Local Demo

## Status

Accepted.

## Context

The product requirements prefer Redis JSON for catalog documents but allow Hash storage when justified. The demo needs a one-command local startup, vector fields, exact filtering, RedisVL index lifecycle, and a small synthetic corpus.

## Decision

Gift-card products are stored as Redis Hashes under `demo:giftcard:{id}` and indexed by Redis Search through the `demo:giftcards` alias. Arrays are flattened into pipe-separated TAG fields, and vector embeddings are stored as FLOAT32 byte buffers.

Profiles, tenants, promotions, routes, search events, and evaluation runs are stored as JSON strings under namespaced Redis keys.

## Consequences

- The search index is fast, flat, and easy to inspect with `HGETALL`.
- RedisVL can create and validate the Hash schema directly.
- The demo does not require RedisJSON-specific commands for the main catalog path.
- Nested document updates are less expressive than RedisJSON; that is acceptable for the synthetic catalog and documented as a local-demo trade-off.


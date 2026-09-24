# GiftFind RedisVL Relevance Lab

A local retail search demo for Redis Solutions Architects. The built-in Blackhawk
Network (BHN) experience uses gift cards to show text search, hybrid search,
reranking, semantic routing, and bounded personalization.

**Start with the [SA Install and Run Guide](docs/install-and-run.md).** It covers
setup, model warmup, daily use, retailer imports, and troubleshooting. For the
customer story, use the [Demo Walkthrough](docs/demo-walkthrough.md).

The catalog includes a static public GiftCards.com assortment snapshot and
synthetic examples. It is not a live commerce feed. Prices, availability, profiles,
and service actions are demo data.

## First-Time Setup

Install Git and a Docker runtime with Docker Compose. You do not need a local
Python or Node.js install, a GPU, or a paid AI API key.

```bash
git clone https://github.com/bcooper-redis/BHN-Reranking-Demo.git redisvl-retail-demo
cd redisvl-retail-demo
cp .env.example .env
docker compose up -d --build
```

This startup path runs the seed service, which resets and loads the built-in BHN
catalog. First-time downloads may take several minutes or longer. For later runs,
use the [startup steps that preserve data](docs/install-and-run.md#start-again-without-resetting-data).

If another Redis instance uses port `6379`, change `REDIS_PORT` in `.env` to `6380`.
Keep `REDIS_URL=redis://redis:6379` for communication inside Docker.

Open the [demo](http://localhost:5173/),
[retailer configuration](http://localhost:5173/?view=configuration), or
[API reference](http://localhost:8000/docs).

Check the services and catalog:

```bash
docker compose ps -a
curl --fail --show-error http://localhost:8000/health/ready
curl --fail --show-error -H 'X-Demo-Retailer: bhn' \
  http://localhost:8000/api/v1/config/public
```

The seed service should finish with exit code `0`. The API should report Redis as
connected, and the BHN config should show `catalog_count: 360`. The ready endpoint
checks Redis connectivity only. It does not check catalog contents or model
warmup. Follow the guide's search checks before a meeting.

**Local demo only:** the app has no login or API authentication. Compose publishes
ports on all host interfaces by default. Use a trusted environment and follow your
team's firewall rules. Do not expose the app or Redis to the public internet.

## Demo Paths

| Path | What it shows |
| --- | --- |
| Customer search | Run text search, add hybrid retrieval, then rerank candidates |
| Short-prefix discovery | Search `Star` as text, then enable prefix matching to find Starbucks |
| Exact-brand confidence | Keep an eligible exact-brand match ahead of other candidates |
| Service routing | Return a simulated service action before product retrieval |
| Bounded personalization | Apply a small profile boost after relevance scoring |

Each search button makes a new request. **Continue** changes the step without
running it. A reranked request runs hybrid retrieval again before the cross-encoder.
The UI can switch between RedisVL's local MiniLM L6 and TinyBERT L2 rerankers.
Warm each model before comparing it. No Cohere or Voyage adapter is implemented.

Prefix search and typeahead start off. Typeahead makes a separate Redis prefix
lookup while you type. Selecting a suggestion fills the field and immediately
runs the current search step with the active demo settings.

Open **Execution and timing** or **Redis Search queries** to show the actual work.
The [walkthrough](docs/demo-walkthrough.md) explains the full presentation flow.

## Custom Retailer Demos

Use the gear icon to open the configuration page. The Demo Foundry provides a
copyable prompt for a downloadable JSON catalog. Generate the file in ChatGPT,
download it, upload it, name the demo, and click **Generate retailer demo**.
Wait for **Generation complete** before opening it.

The current prompt requests exactly 360 synthetic products, website-inspired
colors, and catalog-based search prompts. Discovery prompts ask for one item in
6-10 words. The generated paths include a short-prefix example and a service route.
The [example JSON](docs/demo-foundry-example.json) shows the format, but is too
small to upload as a complete catalog.

Each custom retailer uses its own `demo:<retailer-id>:*` keys and indexes. Saved
configurations reload from Redis when the API starts. The browser remembers its
selection and sends an `X-Demo-Retailer` header with requests.

Importing the same organization replaces its demo. Keep original JSON files as
backups. The configuration page can delete custom demos; BHN is protected.
See the [full import and delete steps](docs/install-and-run.md#create-or-delete-a-retailer-demo).

Product images are optional. Missing or failed images use branded placeholders.
See [Product Artwork and Sources](docs/product-images.md).

## Scorecard and Load Testing

The golden query scorecard compares search results against stored demo judgments.
It reports ranking quality, route accuracy, and latency. Higher ranking scores do
not guarantee better results for every customer query.

Milestone 7 adds a bounded load test. Warm the selected reranker, open **Golden
query scorecard and load testing**, choose concurrency `2`, and run the test. BHN
uses four product queries, three rounds, and three modes: 12 requests per mode.
The report includes p50, p95, fallbacks, and errors. It saves the chosen model and
settings with the result.

These small laptop runs are demo observations, not production capacity tests.
Compare warmed runs with the same settings. Concurrency `4` adds more local CPU
pressure. Browser round-trip time includes more work than Redis retrieval time.

## Stop and Restart

```bash
docker compose stop
```

To start again without running the seed service:

```bash
docker compose up -d --no-deps redis
docker compose exec redis redis-cli ping
```

Wait for `PONG`, then run:

```bash
docker compose up -d --no-deps api frontend
```

To restart only the application:

```bash
docker compose restart api frontend
```

This keeps Redis data. Warm the models again after an API restart. Use the guide
for [updates](docs/install-and-run.md#get-code-updates),
[settings](docs/install-and-run.md#settings), and
[data resets](docs/install-and-run.md#reset-data).

## Architecture and Code

| Component | Stack | Main code |
| --- | --- | --- |
| Web interface | React, TypeScript, Vite | `frontend/src/pages/` |
| API and retrieval | FastAPI, redis-py, RedisVL | `backend/app/retrieval/catalog.py` |
| Local rerankers | RedisVL `HFCrossEncoderReranker` | `backend/app/reranking/provider.py` |
| Semantic routing | RedisVL `SemanticRouter` | `backend/app/routing/service.py` |
| Retailer setup | Built-in registry and runtime imports | `backend/app/retailers/` |
| Data and search | Redis 8.4, Hashes, Redis Search | `backend/app/redis/catalog_index.py` |

BHN uses keys such as `demo:bhn:giftcard:{id}`, physical index
`demo:bhn:giftcards:v1`, and search alias `demo:bhn:giftcards`. Tenant and active
filters apply before ranking. Hybrid retrieval uses text and vector queries, then
application-side reciprocal rank fusion. Eligible exact-brand matches stay
protected after reranking and policy scoring.

The [Redis Search Flows PDF](docs/redis-search-flows.pdf) provides five
customer-neutral engineering diagrams covering retrieval, prefix search and
typeahead, exact-match protection, routing, and personalization. Each flow shows
what runs in Redis, what runs in the application, and why.

See [ADR 0001](docs/decisions/0001-redis-hash-search-index.md) for the original
storage decision. The [Requirements folder](Requirements/README.md) records the
build plan; some planned features differ from the current implementation. Use
the code and install guide for current behavior.

## Developer Checks

The Docker images run the demo. They do not include the full test environment.
For local development, use Python 3.12 or later with the backend's `dev` extras,
and Node.js 22 with `npm ci` in `frontend`.

The `Makefile` provides test and lint commands once those local tools are installed.
`make backend-integration-test` needs a seeded Redis instance and defaults to host
port `6380`; set `REDIS_URL` explicitly if yours differs. `make seed` resets BHN
data, so do not use it as a health check.

# SA Install and Run Guide

This guide helps a Redis Solutions Architect (SA) install the demo, check that it
works, and prepare for a customer meeting. You do not need to change application
code or install Python or Node.js on your laptop.

The project starts with GiftFind, the Blackhawk Network (BHN) gift card demo. You
can also create a retailer demo with its own name, colors, products, and search
prompts. Each retailer has separate data and search indexes in Redis.

## Contents

- [Before you start](#before-you-start)
- [Install and start the demo](#install-and-start-the-demo)
- [Check the installation](#check-the-installation)
- [Warm up before a meeting](#warm-up-before-a-meeting)
- [Run the five demo paths](#run-the-five-demo-paths)
- [Create or delete a retailer demo](#create-or-delete-a-retailer-demo)
- [Stop, start, and update](#stop-start-and-update)
- [Settings](#settings)
- [Troubleshooting](#troubleshooting)
- [Reset data](#reset-data)
- [Get help](#get-help)

## Before you start

### Tools and access

Install Git and a Docker runtime with Docker Compose. Use your company-approved
Docker setup and license. Start Docker before running the commands below.

| Your system | Setup | Where to run the commands |
| --- | --- | --- |
| Mac | [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) | Terminal, using zsh or Bash |
| Windows | [Docker Desktop with WSL 2](https://docs.docker.com/desktop/setup/install/windows-install/) and a Linux distribution such as Ubuntu | The WSL Linux terminal, with Docker integration enabled |
| Linux | [Docker Engine with the Compose plugin, or Docker Desktop](https://docs.docker.com/compose/install/) | Bash |

Get Git from the [official Git download page](https://git-scm.com/downloads/).
The commands in this guide use a Unix-style shell. Do not paste them into Windows
Command Prompt or PowerShell without adapting them.

You also need access to the GitHub repository and an internet connection for the
first build. Docker downloads images and packages. The backend downloads public
Hugging Face models. No paid AI API key or GPU is required for the built-in demo.

As a planning starting point, use a laptop with 16 GB of RAM and 20 GB of free disk
space. Give Docker enough memory and CPU to run local models. These are practical
starting points, not tested minimum requirements. Close other model-heavy apps
before a live demo.

Check your tools:

```bash
git --version
docker version
docker compose version
```

`docker version` should show both a client and a server. If it cannot reach the
server, start Docker Desktop or your Docker service first.

### Use a local, trusted environment

This is a demo, not a production service. It has no login or API authentication.
The default Compose file publishes ports on all host network interfaces. Do not
expose it to the internet or an untrusted network. Follow your team's firewall
rules. The configuration page is a presenter tool, not a security boundary.

Use synthetic data only. The BHN catalog includes a static public assortment
snapshot and synthetic examples. It does not show live prices or inventory.
Service actions, such as checking a card balance, are simulated.

## Install and start the demo

### 1. Get the project

```bash
git clone https://github.com/bcooper-redis/BHN-Reranking-Demo.git redisvl-retail-demo
cd redisvl-retail-demo
```

If Git reports that the repository was not found, sign in to GitHub and ask the
repository owner for access. Do not put a token in a command or share it in a
support request.

Run all remaining terminal commands from this project folder. Keep using the same
folder. Docker Compose uses the folder name to identify its containers and data
volumes unless you set a different project name.

### 2. Create the settings file

```bash
cp .env.example .env
```

Do this once for a new checkout. Do not overwrite an existing `.env` when updating.
The file stays local and Git ignores it.

For the standard Docker setup, confirm these values in `.env`:

```dotenv
REDIS_URL=redis://redis:6379
REDIS_PORT=6379
RERANK_TIMEOUT_MS=3000
FRONTEND_ORIGIN=http://localhost:5173
VITE_API_BASE_URL=http://localhost:8000
```

If another Redis instance already uses port `6379`, set `REDIS_PORT=6380` instead.
Leave `REDIS_URL=redis://redis:6379` unchanged. The first setting controls the port
on your laptop. The second tells containers how to reach the demo's Redis service.
This starts a separate Redis instance and does not reuse your other Redis data.

Ports `5173` and `8000` must also be free. See [Port already in use](#port-already-in-use)
if either is occupied.

### 3. Build and start

**First-time setup only:** this command can run the seed service. That service
resets the built-in BHN data before loading it. Use the later [daily startup
steps](#start-again-without-resetting-data) to keep existing data.

```bash
docker compose up -d --build
```

The `-d` option runs the containers in the background. The first build can take
several minutes or longer, depending on your connection and laptop.

Compose starts four services:

| Service | Job | Expected state after setup |
| --- | --- | --- |
| `redis` | Stores products, vectors, routes, and demo data | Running and healthy |
| `seed` | Loads 360 BHN cards, creates indexes, and prepares route data | Exited with code `0` |
| `api` | Runs search, local models, and demo tools | Running |
| `frontend` | Serves the web interface | Running |

Watch setup progress:

```bash
docker compose ps -a
docker compose logs -f seed api
```

Press **Ctrl+C** to stop watching logs. This does not stop the containers. A seed
container that exits with code `0` is normal. A nonzero exit code means setup
failed. Read its logs before trying again.

## Check the installation

### 1. Check the API and Redis

```bash
curl --fail --show-error http://localhost:8000/health/live
curl --fail --show-error http://localhost:8000/health/ready
```

Expected responses:

```json
{"status":"ok","service":"giftfind-api"}
```

```json
{"status":"ready","redis":"connected","environment":"local"}
```

The live check confirms that the API responds. The ready check confirms that it
can reach Redis. **Neither check proves that the catalog is loaded or the models
are warm.** Complete the next checks too.

### 2. Check the BHN catalog

```bash
curl --fail --show-error -H 'X-Demo-Retailer: bhn' \
  http://localhost:8000/api/v1/config/public
```

Look for `"catalog_count":360` and retailer ID `bhn`. The response also lists the
available rerankers. A new install has BHN only. Your existing install may also
list custom retailers you have created.

Check the prefix index:

```bash
curl --fail --show-error -H 'X-Demo-Retailer: bhn' \
  'http://localhost:8000/api/v1/search/suggestions?q=Star&tenant_id=general'
```

The suggestions should include `Starbucks eGift`. This endpoint checks the
suggestion service even when typeahead is off in the browser.

### 3. Open the app

- [Demo](http://localhost:5173/)
- [Retailer configuration](http://localhost:5173/?view=configuration)
- [API reference and test page](http://localhost:8000/docs)

Use `localhost` as shown. Mixing `localhost` and `127.0.0.1` can cause browser
origin errors with the default settings.

Open the configuration page using the gear icon. Select BHN and click **Open
prepared demo**. Confirm that the app shows **Redis connected**, 360 catalog
cards, and the **Customer search** path.

## Warm up before a meeting

Model files remain in a Docker volume, but the running API must load models into
memory after a restart. A fast Redis response does not mean a model is ready.

1. Select **Customer search** and keep the prefilled coffee query.
2. Click **Run text search**. This also warms the semantic router.
3. Click **Continue: Add semantic retrieval**, then **Add semantic signal**.
4. Continue to the reranker step and click **Run cross-encoder**.
5. Open **Execution and timing**. Check the reranker details and any fallback.
6. If the first reranked request fell back during model loading, wait and run it again. Confirm a successful reranker result before presenting it as reranked.
7. If you will switch models, select **TinyBERT L2 (fast)** and run that step too. Then return to the model you want to use first.
8. Reset the path before the customer arrives. Confirm that both prefix and typeahead controls are off for the initial text-search story.

**Continue** selects the next step. It does not execute a search. Each search
button sends a new request. A reranked request runs hybrid retrieval again before
it calls the selected cross-encoder.

Keep the app running after warmup. Test the full walkthrough before presenting
without internet access. Uncached models and remote product images can still need
a connection. Missing images use placeholders.

## Run the five demo paths

Use the Path selector to choose the story. Let each step finish before moving on.
The [demo walkthrough](demo-walkthrough.md) has more presentation detail.

| Path | What to do | What it shows |
| --- | --- | --- |
| Customer search | Run text search, add the semantic signal, then run the cross-encoder | Text matching, hybrid retrieval, and reranking as separate steps |
| Short-prefix discovery | Search `Star` with prefix off, then continue and run with prefix on | Entertainment text can match first; prefix matching brings in Starbucks |
| Exact-brand confidence | Find `Best Buy`, then verify the exact match with reranking | Eligible exact-brand matches keep priority |
| Service routing | Run `check my balance` | A service action can bypass product retrieval and reranking |
| Bounded personalization | Search anonymously, then apply the Tech Buyer profile | A small profile boost can reorder the returned cards |

For typeahead, enable **Typeahead suggestions** and type `Star`. Suggestions begin
at three characters. Click Starbucks, or highlight it with the arrow keys and
press Enter, to fill the search field and immediately run the current search
step. The active demo settings stay unchanged. Typeahead and prefix search are
separate controls.

Do not promise that every step changes the top result. Relevant cards can stay in
the same order. Personalization only adjusts the returned set, and exact matches
remain protected.

Use the panels below the results when someone asks for detail:

- **Execution and timing** shows the call sequence, route, model, and policy data.
- **Redis Search queries** shows the actual Redis Search statements.
- **Golden query scorecard and load testing** provides repeatable checks.

### Scorecard and load test

Run the scorecard to compare the three search modes against a small set of stored
test queries and expected results. It is a demo check, not a customer benchmark.

Warm the selected reranker first. Start the load test at concurrency `2`, which
allows two requests to overlap. The BHN default runs 12 requests per search mode.
It reports errors, fallbacks, p50, and p95. The p50 is the median time. The p95 is
the time at or below which about 95% of requests finish.

This is a small sample on a laptop. It does not measure production capacity. Keep
the model, query set, and concurrency the same when comparing runs. A local model
can use far more time than Redis retrieval. Browser round-trip time and Redis
retrieval time measure different parts of the request.

## Create or delete a retailer demo

### Create a demo

1. Open the gear icon or the [configuration page](http://localhost:5173/?view=configuration).
2. Expand **ChatGPT catalog prompt** and click **Copy prompt**.
3. Use that prompt in ChatGPT and replace the website placeholder with the retailer's website. Ask for the downloadable JSON file as the prompt directs.
4. Download the file. It must contain exactly 360 synthetic products, the palette, and the catalog-based demo paths. Use the current prompt, not an older copy.
5. Upload the file under **Catalog file** and review the **Demo name**.
6. Click **Generate retailer demo** once. Wait while the app creates embeddings and search indexes. Do not refresh or submit it again while it is working.
7. Wait for **Generation complete** and the indexed product count. Click **Open generated demo**, then check each path and warm the selected models.

The intended sequence is **Generate file, download, upload, generate demo**. The
app does not call ChatGPT itself. The current prompt asks for one item per
discovery query, with 6-10 words. It also asks for a prefix scenario supported by
the generated catalog.

Keep the original JSON file as a backup. The small
[Foundry example](demo-foundry-example.json) explains the file format, but it does
not contain the 360 products required by the upload screen.

**Replacement warning:** the app uses `organization_name` to derive the retailer
ID. Importing the same organization again replaces that retailer's existing data.
Changing only the display name does not create a separate copy.

The browser remembers the selected retailer. Custom catalogs and their saved
configuration live in Redis and reload when the API starts. Keep the Redis data
volume. The saved upload can recreate a catalog, but it does not back up later
events or evaluation history.

### Delete a demo

Select the custom retailer on the configuration page, click **Delete custom
demo**, and confirm with **Delete demo**. This removes its catalog, search index,
routes, cached data, events, evaluations, and saved configuration. There is no
undo. The UI protects BHN from deletion.

## Stop, start, and update

### Stop without deleting data

```bash
docker compose stop
```

This keeps the containers and both data volumes. `docker compose down` also keeps
volumes by default, but removes containers. Neither command is a backup.

### Start again without resetting data

Start Redis first:

```bash
docker compose up -d --no-deps redis
docker compose exec redis redis-cli ping
```

Wait for `PONG`. If Redis is still starting, wait a few seconds and repeat the
ping command. Then start the application:

```bash
docker compose up -d --no-deps api frontend
```

The `--no-deps` option keeps Compose from starting the seed service through a
dependency. This is the routine startup path after initial setup. Check readiness,
catalog count, and model warmup again.

### Restart a stuck API or web interface

```bash
docker compose restart api frontend
```

This preserves Redis data and does not run the seed service. Model memory is cold
after an API restart. A restart does not rebuild images or load changed Compose
environment settings.

### Get code updates

Start Redis and confirm `PONG` first. Check for local edits before pulling:

```bash
git status
```

If Git reports local changes, stop and resolve them before continuing. Do not
discard local work just to update the demo. When the working tree is clean, pull:

```bash
git pull --ff-only
```

If the pull fails, stop and resolve the error. After a successful pull, build:

```bash
docker compose build api frontend seed
```

After the build succeeds, start the updated application:

```bash
docker compose up -d --no-deps api frontend
```

Rebuilding `seed` keeps its image current for a future reset. It does not run the
seed job.

These steps preserve existing Redis data. If a release changes the catalog or
index schema, follow its migration instructions. Rebuilding containers alone does
not update stored catalogs. Recheck custom demos after an update.

## Settings

The main Docker settings are below. Edit `.env` in the project root.

| Setting | Standard value | Purpose |
| --- | --- | --- |
| `REDIS_URL` | `redis://redis:6379` | Redis address seen by the backend containers |
| `REDIS_PORT` | `6379` | Published Redis port on your laptop |
| `RERANK_TIMEOUT_MS` | `3000` | Time budget for a local reranker operation, in milliseconds |
| `ROUTER_TIMEOUT_MS` | `30000` | Time budget for semantic routing |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Browser origin the API accepts |
| `VITE_API_BASE_URL` | `http://localhost:8000` | API address the browser calls |

After changing the API or frontend settings, recreate those containers:

```bash
docker compose up -d --no-deps --force-recreate api frontend
```

After changing only `REDIS_PORT`, recreate Redis with
`docker compose up -d --no-deps redis`, wait for `PONG`, then restart the API.

Compose does not pass every variable in `.env` into the containers. It passes the
variables listed in `docker-compose.yml`. Some entries in `.env.example` are
older settings or apply only to a separately run backend. In particular:

- Use the UI to switch between MiniLM L6 and TinyBERT L2. The current app supports those local rerankers. Adding Cohere or Voyage credentials does not enable an adapter in the current code.
- `ADMIN_TOKEN` does not enable authentication.
- The retailer definition sets index and router names. The old `REDIS_INDEX_ALIAS` and `ROUTER_NAME` entries do not change those names.
- Keep the built-in `RETAILER_ID` at `bhn`. Choose custom retailers in the configuration screen instead.

### Using hosted Redis

Prove the local setup first. For a hosted test, use a **dedicated demo database**
with Redis Search and vector search support. Match the Redis 8.4 feature set used
by this project. The seed job resets demo keys and indexes on its target database.
Do not point it at a shared customer or production database.

Set the provider's connection URL in `REDIS_URL`, using `rediss://` when TLS is
required. Keep credentials in `.env`, never in Git, screenshots, or shared logs.
The current Compose setup still starts its local Redis container, even when the
backend targets hosted Redis. Changing the URL does not migrate data. Recreate
the API and seed the dedicated target only when you intend to initialize it.

The standard path in this guide is local Docker. Hosted credentials, certificates,
network access, and deployment security need separate validation.

## Troubleshooting

### The page stays on Checking runtime

Run these checks in order:

```bash
docker compose ps -a
docker compose logs --tail=100 seed api frontend
docker compose exec redis redis-cli ping
curl --fail --show-error http://localhost:8000/health/ready
curl --fail --show-error -H 'X-Demo-Retailer: bhn' \
  http://localhost:8000/api/v1/config/public
```

- No API container: check whether the seed job failed or is still downloading.
- No `PONG`: check Redis logs and Docker's status first.
- Ready works, config fails: check the API logs for a missing catalog, index, or tenant record. A Redis ping alone does not check these.
- API calls work, page does not: reload the page and check browser developer tools for network or origin errors. Confirm the two frontend URL settings.
- Custom retailers are missing after a Redis outage: once Redis responds, restart the API so it reloads their saved configurations.

Try a fresh browser window if it is holding an old retailer selection. Do not
reset Redis as the first troubleshooting step.

### Port already in use

For Redis, change `REDIS_PORT` in `.env` to `6380` or another free port. Keep the
container URL at `redis://redis:6379`.

For ports `5173` or `8000`, stop the conflicting app if it is safe to do so. If you
must use different ports, change the **host side** of the matching port mapping
in `docker-compose.yml`. Also update `FRONTEND_ORIGIN` and `VITE_API_BASE_URL` to
match the browser URLs. Recreate the API and frontend containers. Do not kill an
unknown process just to free a port.

### Downloads fail or setup appears slow

Check `docker compose logs seed` and the build output. The first run downloads
Python packages, CPU-only PyTorch, and model files. Check disk space, your VPN,
proxy settings, and access to Docker registries, PyPI, the PyTorch download site,
and Hugging Face. Follow company policy for network or certificate issues; do
not turn off TLS checks.

If a failed first setup needs another attempt, run
`docker compose up -d --build` again after fixing the cause. Remember that this is
the seed/reset startup path.

### Search is slow, or reranking falls back

Warm both the router and the selected reranker. Check **Execution and timing** to
separate Redis retrieval from model work. A first request can spend most of its
time loading a model, even when Redis is fast.

If `.env` came from an older checkout, it may set `RERANK_TIMEOUT_MS=250`. Change
it to `3000`, then recreate the API with
`docker compose up -d --no-deps --force-recreate api`. A plain restart will not
apply a changed Compose value.

A reranker error can return hybrid results. Results on screen do not prove that
reranking succeeded. Check the fallback reason and selected model, close other
CPU-heavy apps, then retry after warmup. A larger timeout permits a longer wait;
it does not make the model faster.

### Star does not return Starbucks

In BHN's **Short-prefix discovery** path, this is expected with prefix search off.
Turn on **Brand prefix search** and run the search again. Typeahead uses a separate
toggle and needs at least three characters. Make sure BHN is the selected retailer
and the tenant is the General Gift Marketplace.

### A custom upload fails

Use the current copied prompt. Confirm valid JSON with exactly 360 products and
catalog-supported demo paths. The upload must contain actual records, not a
sample followed by "repeat this pattern." Check the on-screen error and API logs.

If the request is still running, wait. If it has failed, keep the source file and
investigate before retrying. Reusing an organization name replaces its demo, so
do not use retries as a way to keep separate versions.

## Reset data

Do these steps only when you intend to replace data. Do not use a reset to solve
a slow first search.

### Reset BHN only

This removes BHN's catalog and data under `demo:bhn:*`, including its cached
embeddings, events, and saved evaluation results, then loads 360 BHN cards again.
It leaves custom retailer namespaces and their saved configurations intact.
The current seed registry contains BHN only.

With Redis running and responding to `PING`, build the current images:

```bash
docker compose build seed api
```

After a successful build, stop the API and run the BHN reset:

```bash
docker compose stop api
docker compose run --rm --no-deps seed python -m app.seed --reset --count 360
```

If the seed job fails, stop here and check the error. After it exits successfully,
start the API:

```bash
docker compose up -d --no-deps api
```

Recheck the catalog count and warm the models. The explicit seed command above
omits the legacy cleanup flag used by the first-time Compose startup.

### Remove all local demo data

**Destructive:** this deletes this Compose project's Redis volume and model cache.
It removes BHN, all custom demos, and their history from the local Redis volume.
Keep custom catalog JSON files before proceeding. Models must download again.

```bash
docker compose down --volumes
docker compose up -d --build
```

This full reset applies to the standard local setup. It does not delete a hosted
Redis database. Avoid global commands such as `FLUSHALL` or Docker system prune.

## Get help

Before sharing a problem, collect:

- The command or UI step that failed and the exact error.
- Your operating system and CPU type.
- Output from `git rev-parse --short HEAD` and `docker compose version`.
- Output from `docker compose ps -a` and recent logs for the failing service.
- Health-check results, retailer, demo path, selected reranker, and fallback code.

Remove passwords, tokens, connection URLs with credentials, and customer data
before sharing logs or screenshots. Do not share `.env` or a full resolved
Compose configuration if it contains secrets.

For code details, start with `backend/app/retrieval/catalog.py`,
`backend/app/reranking/provider.py`, and `backend/app/routing/service.py`.

### Guide verification

Checked on September 24, 2026 against the project code and the existing Docker
runtime on macOS. Live checks passed for health, the 360-card BHN catalog,
typeahead, and all three search modes. The no-seed startup command was checked
with a Docker dry run. Clean installs on Windows and Linux were not tested for
this guide. Data reset steps were reviewed, not executed.

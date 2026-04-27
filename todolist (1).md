# PostMortemIQ — Complete Build Todolist
### Ordered Task List: Day-by-Day Build Plan

---

## How to Use This List

Tasks are ordered so each one builds on the previous. Do not skip ahead — the graph must be built before the pipelines, and the pipelines must work before the dashboard. TEE integration happens last so it wraps a working system.

**Estimated total time:** 10–12 days for a solo developer (2–3 hours/day)

**Legend:**
- `[MUST]` — Required for hackathon submission
- `[SHOULD]` — Strongly recommended, adds significant judge impact
- `[BONUS]` — Nice to have, builds toward community prize

---

## PHASE 1 — Setup & Foundation
### Day 1 — Environment & Accounts

- [ ] `[MUST]` Create TigerGraph Cloud account at tgcloud.io (free tier)
- [ ] `[MUST]` Create a new TigerGraph cloud instance (choose smallest free-tier option)
- [ ] `[MUST]` Create Groq API account at console.groq.com (free tier)
- [ ] `[MUST]` Save Groq API key securely (never commit to git)
- [ ] `[MUST]` Create GitHub repository: `postmortemiq`
- [ ] `[MUST]` Set up Python virtual environment: `python -m venv .venv`
- [ ] `[MUST]` Install core dependencies:
  ```
  pip install pyTigerGraph fastapi uvicorn streamlit tiktoken
  pip install groq httpx asyncio pyvis faker cryptography grpcio
  ```
- [ ] `[MUST]` Create project folder structure:
  ```
  postmortemiq/
  ├── graph/
  │   ├── schema.py
  │   ├── queries.py
  │   └── load_graph.py
  ├── pipelines/
  │   ├── baseline.py
  │   ├── graphrag.py
  │   └── comparator.py
  ├── orchestration/
  │   └── router.py
  ├── llm/
  │   ├── prompt_builder.py
  │   └── response_verifier.py
  ├── tee/
  │   ├── enclave_runner.py
  │   ├── attestation.py
  │   └── key_manager.py
  ├── evaluation/
  │   └── dashboard.py
  ├── data/
  │   └── generate_incidents.py
  ├── docs/
  │   ├── architecture.md
  │   ├── design.md
  │   └── requirements.md
  ├── main.py
  ├── requirements.txt
  └── README.md
  ```
- [ ] `[MUST]` Create `.env` file with API keys (add to .gitignore immediately)
- [ ] `[MUST]` Create `.gitignore` (include `.env`, `__pycache__`, `.venv`)
- [ ] `[MUST]` Write initial README.md with project description and setup steps

---

## PHASE 2 — Graph Layer
### Day 2 — TigerGraph Schema & Data Model

- [ ] `[MUST]` Define vertex types in TigerGraph Studio:
  - `Alert` (alert_id, name, severity, timestamp, status)
  - `Service` (service_id, name, team_owner, sla_tier, language, repo_url)
  - `Deployment` (deploy_id, version, timestamp, deployer, diff_summary)
  - `ConfigChange` (change_id, key, old_value, new_value, timestamp, changer)
  - `Dependency` (dep_id, name, version_pinned, type)
  - `Team` (team_id, name, on_call_engineer, escalation_path, pagerduty_id)
  - `Runbook` (runbook_id, title, steps_summary, last_used, url)
  - `Incident` (incident_id, severity, start_time, end_time, status)

- [ ] `[MUST]` Define edge types in TigerGraph Studio:
  - `fired_on` (Alert → Service, timestamp)
  - `had_deployment` (Service → Deployment, at_timestamp)
  - `changed_config` (Deployment → ConfigChange)
  - `broke_dependency` (ConfigChange → Dependency, confidence_score)
  - `used_by` (Dependency → Service)
  - `owned_by` (Service → Team)
  - `has_runbook` (Service → Runbook, issue_type)
  - `calls` (Service → Service, protocol, timeout_ms)
  - `part_of` (Alert → Incident)

- [ ] `[MUST]` Verify schema loads correctly in TigerGraph Studio
- [ ] `[MUST]` Write `schema.py` that programmatically verifies the schema using pyTigerGraph
- [ ] `[SHOULD]` Add schema diagram to README using ASCII art or Mermaid

### Day 3 — Synthetic Data Generator

- [ ] `[MUST]` Write `generate_incidents.py` with the following functions:
  - `generate_services(n=10)` — creates realistic microservice names and configs
  - `generate_teams(n=5)` — creates on-call teams with engineer names
  - `generate_deployments(n=25)` — creates deployment events with realistic diff summaries
  - `generate_config_changes(n=30)` — creates config mutations (env vars, feature flags)
  - `generate_runbooks(n=15)` — creates remediation runbooks with step summaries
  - `generate_incidents(n=25)` — creates incidents with KNOWN ground truth causal chain

- [ ] `[MUST]` Ensure each synthetic incident specifies:
  - `ground_truth_root_cause` (which ConfigChange caused it)
  - `ground_truth_affected_services` (list of services impacted)
  - `ground_truth_unpaged_teams` (teams not yet alerted)
  - `hop_depth` (2, 4, or 6 — for varied benchmark testing)

- [ ] `[MUST]` Create at least 8 incidents with 2-hop chains, 10 with 4-hop, 7 with 6-hop
- [ ] `[MUST]` Save generated data to `data/synthetic_incidents.json`

### Day 4 — Graph Loading & GSQL Queries

- [ ] `[MUST]` Write `load_graph.py` that:
  - Connects to TigerGraph Cloud using pyTigerGraph
  - Loads all vertex types from synthetic data
  - Loads all edge types with correct directionality
  - Prints a loading summary (X vertices loaded, Y edges loaded)

- [ ] `[MUST]` Run `load_graph.py` and verify data appears in TigerGraph Studio
- [ ] `[MUST]` Write and test GSQL query `blast_radius(incident_id, max_hops)` in TigerGraph Studio
- [ ] `[MUST]` Write and test GSQL query `root_cause_chain(alert_id)` in TigerGraph Studio
- [ ] `[MUST]` Write and test GSQL query `unpaged_teams(incident_id)` in TigerGraph Studio
- [ ] `[SHOULD]` Write and test GSQL query `runbook_matcher(service_id, issue_type)`
- [ ] `[MUST]` Install all queries to TigerGraph Cloud (make them callable via API)
- [ ] `[MUST]` Write `queries.py` — Python wrapper functions for each GSQL query
- [ ] `[MUST]` Verify all queries return correct results against known ground truth incidents
- [ ] `[MUST]` Measure and record query latency for all 4 queries (target: < 200ms each)

---

## PHASE 3 — Pipelines
### Day 5 — Baseline LLM Pipeline

- [ ] `[MUST]` Write `pipelines/baseline.py`:
  - `assemble_context(incident_id)` — builds full raw context from mock data
  - Includes: alert text (~500 tokens), log excerpts (~3,000 tokens), deployment notes (~2,000 tokens), config history (~1,500 tokens), dependency docs (~2,000 tokens)
  - Total context must exceed 8,000 tokens
  - Returns assembled prompt string

- [ ] `[MUST]` Write `llm/prompt_builder.py`:
  - `build_baseline_prompt(context)` — wraps raw context in LLM prompt
  - `build_graphrag_prompt(subgraph)` — wraps graph subgraph in LLM prompt
  - Both prompts ask the same question: "What is the root cause of this incident?"

- [ ] `[MUST]` Write Groq API client in `llm/groq_client.py`:
  - `call_llm(prompt, model="mixtral-8x7b-32768")` → returns response text
  - Records: input_tokens, output_tokens, latency_ms
  - Handles rate limit errors with exponential backoff

- [ ] `[MUST]` Count tokens using `tiktoken` BEFORE sending to API
- [ ] `[MUST]` Write baseline pipeline end-to-end test using 3 synthetic incidents
- [ ] `[MUST]` Record baseline results: confirm context > 8,000 tokens, latency > 2,000ms typically

### Day 6 — GraphRAG Pipeline

- [ ] `[MUST]` Write `pipelines/graphrag.py`:
  - `get_causal_subgraph(incident_id)` — calls TigerGraph GSQL queries
  - `format_subgraph_as_context(subgraph)` — converts graph nodes/edges to structured text
  - `build_graphrag_prompt(subgraph_context)` — assembles minimal LLM prompt
  - Returns RCA result with token count and latency

- [ ] `[MUST]` Ensure formatted subgraph context stays under 600 tokens
- [ ] `[MUST]` Write `llm/response_verifier.py`:
  - `extract_entities(response_text)` — extracts service names, config keys, team names mentioned in LLM response
  - `detect_hallucinations(entities, subgraph)` — identifies entities not present in the retrieved subgraph
  - Returns `HallucinationReport(count, rate, entities)`

- [ ] `[MUST]` Write GraphRAG pipeline end-to-end test using same 3 synthetic incidents as baseline test
- [ ] `[MUST]` Verify GraphRAG accuracy: does identified root cause match `ground_truth_root_cause`?

### Day 7 — Orchestration & Comparator

- [ ] `[MUST]` Write `orchestration/router.py`:
  - `FastAPI` app with routes: `POST /incident`, `GET /benchmark`, `GET /health`
  - `POST /incident` accepts `{incident_id: str}` and runs both pipelines
  - Runs baseline and GraphRAG in parallel using `asyncio.gather()`

- [ ] `[MUST]` Write `pipelines/comparator.py`:
  - `compare(baseline_result, graphrag_result, ground_truth)` → `ComparisonResult`
  - Computes: token_delta, token_reduction_pct, latency_delta, cost_baseline, cost_graphrag, cost_savings_pct, accuracy_baseline, accuracy_graphrag, hallucination_delta
  - Calculates cost using Groq pricing: input $0.27/1M tokens, output $0.27/1M tokens (update with current pricing)

- [ ] `[MUST]` Write `GET /benchmark` handler that runs all 25 synthetic incidents and aggregates metrics
- [ ] `[MUST]` Test full orchestration: `uvicorn main:app --reload` → POST /incident → receive comparison result
- [ ] `[SHOULD]` Add request/response logging (to a file inside the enclave later)

---

## PHASE 4 — TEE Integration
### Day 8 — TEE Setup & Key Management

- [ ] `[MUST]` Install Gramine: `sudo apt-get install gramine` (or follow Gramine docs for your OS)
- [ ] `[MUST]` Install SGX PSW and driver (simulation mode: `SGX=1 SGX_DEBUG=1`)
- [ ] `[MUST]` Write `tee/key_manager.py`:
  - `derive_sealing_key()` — derives a deterministic encryption key from a static seed (simulates SGX sealing key derivation)
  - `encrypt_data(data: bytes, key: bytes) → bytes` — AES-256-GCM encryption
  - `decrypt_data(ciphertext: bytes, key: bytes) → bytes` — AES-256-GCM decryption
  - Uses Python `cryptography` library

- [ ] `[MUST]` Write `tee/attestation.py`:
  - `generate_mrenclave()` — computes SHA-256 hash of the application code directory (simulates MRENCLAVE measurement)
  - `generate_attestation_report()` → returns `{mrenclave: str, timestamp: str, status: "verified"}`
  - `get_attestation_endpoint()` — FastAPI route handler for `GET /attest`

- [ ] `[MUST]` Add `/attest` endpoint to FastAPI app
- [ ] `[MUST]` Verify attestation endpoint returns MRENCLAVE hash and timestamp
- [ ] `[SHOULD]` Write a simple `verify_attestation.py` client script that checks the MRENCLAVE matches expected value

### Day 9 — Enclave Runner & Data Encryption

- [ ] `[MUST]` Write `tee/enclave_runner.py`:
  - `startup_checks()` — verifies Gramine simulation mode is active
  - `load_sealing_key()` — calls `KeyManager.derive_sealing_key()`
  - `decrypt_incident_payload(encrypted_payload)` → plaintext incident JSON
  - `encrypt_result(result_dict)` → encrypted result bytes

- [ ] `[MUST]` Modify `data/generate_incidents.py` to also output encrypted versions of incidents
  - Encrypts each incident JSON using the sealing key
  - Saves both plaintext (for reference) and encrypted (for demo) versions

- [ ] `[MUST]` Modify `POST /incident` handler to:
  - Accept encrypted incident payload
  - Decrypt inside enclave using `enclave_runner.decrypt_incident_payload()`
  - Process through both pipelines
  - Return encrypted result

- [ ] `[SHOULD]` Write Gramine manifest file `postmortemiq.manifest.template`:
  ```
  sgx.enclave_size = "512M"
  sgx.thread_num = 8
  fs.mounts = [{ path = "/app", uri = "file:/app" }]
  ```

- [ ] `[SHOULD]` Run the FastAPI app under Gramine simulation:
  ```bash
  gramine-sgx python main.py
  ```
- [ ] `[SHOULD]` Verify enclave starts, attestation endpoint works, and an encrypted incident is processed correctly

---

## PHASE 5 — Evaluation Dashboard
### Day 10 — Streamlit Dashboard

- [ ] `[MUST]` Write `evaluation/dashboard.py`:
  - Top header: "PostMortemIQ" + TEE status badge (green if enclave active)
  - Aggregate metrics row: token savings %, cost savings %, hallucination rate comparison
  - "Fire Synthetic Incident" button → calls `POST /incident` → refreshes results
  - Side-by-side columns: Baseline vs GraphRAG
  - Per column: tokens, latency, cost, accuracy indicator, LLM response text
  - Graph visualization panel: pyvis rendering of causal subgraph

- [ ] `[MUST]` Add `pyvis` graph rendering:
  - Convert GSQL subgraph result to pyvis Network object
  - Color nodes by type (Alert=red, Service=blue, ConfigChange=orange, Team=green)
  - Display edge labels (fired_on, changed_config, etc.)
  - Embed in Streamlit using `st.components.v1.html()`

- [ ] `[MUST]` Add benchmark panel:
  - Button: "Run Full Benchmark (25 incidents)"
  - Progress bar during run
  - Final scorecard: average token reduction, cost reduction, accuracy delta, hallucination delta

- [ ] `[MUST]` Add TEE attestation panel:
  - MRENCLAVE hash (first 16 chars + "...")
  - Attestation timestamp
  - Status: "Enclave active / Simulation mode"
  - Link to attestation docs

- [ ] `[MUST]` Add ground truth comparison row:
  - Shows expected root cause from `ground_truth_root_cause`
  - Shows match/no-match indicator for each pipeline
  - Highlights token count difference visually (color coded)

- [ ] `[SHOULD]` Add latency waterfall chart showing: graph traversal time vs LLM call time for GraphRAG pipeline
- [ ] `[SHOULD]` Add running cost accumulator: "Total saved across this session: $X.XX"

### Day 11 — Testing & Benchmarking

- [ ] `[MUST]` Run full benchmark across all 25 incidents
- [ ] `[MUST]` Record actual numbers: avg token reduction, avg cost reduction, accuracy, hallucination rates
- [ ] `[MUST]` Verify token reduction exceeds 85% across the benchmark
- [ ] `[MUST]` Verify GraphRAG accuracy exceeds 90% on synthetic ground truth
- [ ] `[MUST]` Verify baseline hallucination rate measurably higher (target: 3x+ higher)
- [ ] `[MUST]` Fix any query failures or pipeline errors discovered during full run
- [ ] `[SHOULD]` Test edge cases: 2-hop incidents, 6-hop incidents, incidents with multiple parallel chains
- [ ] `[SHOULD]` Stress test: run 50 incidents in sequence, verify no rate limit issues

---

## PHASE 6 — Documentation & Submission
### Day 12 — Polish & Submit

- [ ] `[MUST]` Write complete `README.md`:
  - Project overview (2 paragraphs)
  - Architecture diagram (ASCII from architecture.md)
  - Setup instructions (TigerGraph, Groq API key, Python env)
  - How to run: `python data/generate_incidents.py` → `python graph/load_graph.py` → `uvicorn main:app` → `streamlit run evaluation/dashboard.py`
  - How to run benchmark: visit dashboard → click "Run Full Benchmark"
  - TEE setup instructions (Gramine simulation mode)
  - Results table: actual benchmark numbers (token savings, cost savings, accuracy)
  - Links to architecture.md, design.md, requirements.md

- [ ] `[MUST]` Record 3-minute demo video:
  - 0:00–0:20 — Problem statement: "Production incidents lose companies millions. LLMs drown in log noise."
  - 0:20–0:50 — Architecture walkthrough: show 4 layers + TEE wrapper
  - 0:50–1:50 — Live demo: fire a synthetic incident, show baseline (vague, 11,500 tokens) vs GraphRAG (precise, 380 tokens, correct RCA)
  - 1:50–2:20 — Benchmark scorecard: show aggregate numbers across 25 incidents
  - 2:20–2:40 — TEE attestation: show MRENCLAVE hash, explain why this matters for production
  - 2:40–3:00 — Closing: "PostMortemIQ proves graph + TEE = the production-ready future of incident intelligence"

- [ ] `[MUST]` Make GitHub repository public
- [ ] `[MUST]` Verify README setup instructions work from a fresh clone (test in a new venv)
- [ ] `[MUST]` Create Devpost submission with:
  - Project name: PostMortemIQ
  - Description using the hackathon's own language ("tokens, latency, cost, accuracy")
  - Embed benchmark numbers prominently in the description
  - Link to GitHub repo
  - Upload demo video

- [ ] `[SHOULD]` Write a short blog post (dev.to or Medium) about the project: "How I built a TEE-secured GraphRAG incident analyzer"
- [ ] `[BONUS]` Share project in TigerGraph Community Discord/Slack with brief write-up

---

## Quick Reference — Key Numbers to Hit

| Metric | Target | Fail Threshold |
|---|---|---|
| Baseline tokens per query | > 8,000 | < 5,000 (story is weak) |
| GraphRAG tokens per query | < 600 | > 1,500 (advantage not clear) |
| Token reduction | > 85% | < 70% |
| GraphRAG accuracy | > 90% | < 80% |
| Baseline accuracy | < 65% | > 75% (advantage not clear) |
| Hallucination rate gap | GraphRAG < 5%, Baseline > 20% | Gap < 10% |
| GSQL query latency | < 200ms | > 500ms |
| Dashboard response time | < 5s per incident | > 10s |

---

## Checklist for Judges

Print this and check before submitting:

- [ ] TigerGraph graph is live and queryable
- [ ] Both pipelines run end-to-end without errors
- [ ] Dashboard shows side-by-side comparison with all metrics
- [ ] Benchmark runs all 25 incidents and shows aggregate scorecard
- [ ] TEE status is shown in dashboard (even in simulation mode)
- [ ] Attestation endpoint returns MRENCLAVE measurement
- [ ] All components run for ₹0
- [ ] GitHub repo is public with clean README
- [ ] Demo video is under 3 minutes
- [ ] Devpost submission is complete and includes benchmark numbers

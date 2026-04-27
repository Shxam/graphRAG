# PostMortemIQ — Requirements Document
### Functional, Non-Functional, TEE & Hackathon-Specific Requirements

---

## 1. Project Context

PostMortemIQ is a GraphRAG-powered production incident root-cause analysis (RCA) system submitted to the TigerGraph GraphRAG Inference Hackathon. The primary requirement is to prove — with hard, measurable numbers — that a GraphRAG pipeline (TigerGraph + LLM) outperforms a baseline "plain LLM" pipeline on token cost, inference speed, and answer accuracy.

The TEE integration adds a production-grade security layer that protects sensitive incident data throughout the inference pipeline, making PostMortemIQ viable for real-world deployment — not just a hackathon demo.

---

## 2. Functional Requirements

### 2.1 Graph Layer Requirements

| ID | Requirement | Priority |
|---|---|---|
| G-01 | The system shall define a TigerGraph schema with vertex types: Alert, Service, Deployment, ConfigChange, Dependency, Team, Runbook | Must |
| G-02 | The system shall define edge types: fired_on, had_deployment, changed_config, broke_dependency, used_by, owned_by, has_runbook, calls | Must |
| G-03 | The system shall implement a GSQL `blast_radius(incident_id, max_hops)` query that returns all services reachable within N hops of the alert origin | Must |
| G-04 | The system shall implement a GSQL `root_cause_chain(alert_id)` query that traces backwards from an alert to the earliest causal ConfigChange within a 2-hour time window | Must |
| G-05 | The system shall implement a GSQL `unpaged_teams(incident_id)` query that returns teams owning affected services not present in the incident's page group | Must |
| G-06 | The system shall implement a GSQL `runbook_matcher(service_id, issue_type)` query that returns the best matching runbook for the affected service | Should |
| G-07 | The system shall load at least 10 synthetic services, 25 deployments, 30 config changes, 20 incidents, and 15 runbooks into the graph | Must |
| G-08 | All graph queries shall complete within 200ms for graphs up to 1,000 nodes | Must |

### 2.2 Orchestration Layer Requirements

| ID | Requirement | Priority |
|---|---|---|
| O-01 | The system shall expose a FastAPI endpoint `POST /incident` that accepts an incident payload and returns a comparison result | Must |
| O-02 | The system shall run the baseline pipeline and GraphRAG pipeline in parallel (asyncio) for every incident query | Must |
| O-03 | The system shall record per-query metrics: input tokens, output tokens, total tokens, latency (ms), estimated cost (USD), accuracy score | Must |
| O-04 | The system shall record a hallucination count per pipeline per query | Must |
| O-05 | The system shall expose a `GET /benchmark` endpoint that runs all 25 synthetic incidents and returns aggregate metrics | Must |
| O-06 | The system shall expose a `GET /health` endpoint returning enclave status and attestation verification timestamp | Must |

### 2.3 Baseline Pipeline Requirements

| ID | Requirement | Priority |
|---|---|---|
| B-01 | The baseline pipeline shall assemble a full raw context consisting of: alert descriptions, raw log excerpts, deployment notes, config change records, and service dependency documentation | Must |
| B-02 | The baseline context shall be at minimum 8,000 tokens to represent a realistic production incident scenario | Must |
| B-03 | The baseline pipeline shall send the assembled context to the Groq LLM API with no pre-filtering or graph traversal | Must |
| B-04 | The baseline pipeline shall record tokens consumed using `tiktoken` before the API call | Must |

### 2.4 GraphRAG Pipeline Requirements

| ID | Requirement | Priority |
|---|---|---|
| R-01 | The GraphRAG pipeline shall query TigerGraph using GSQL multi-hop traversal to extract the causal subgraph | Must |
| R-02 | The GraphRAG pipeline shall assemble an LLM prompt using only the nodes and edges returned by the GSQL query | Must |
| R-03 | The GraphRAG pipeline context shall not exceed 600 tokens under any tested incident scenario | Must |
| R-04 | The GraphRAG pipeline shall include graph traversal path in the LLM prompt to enable chain-of-evidence reasoning | Must |
| R-05 | The GraphRAG pipeline shall use a ResponseVerifier to detect entities in the LLM output not present in the retrieved subgraph | Must |

### 2.5 LLM Layer Requirements

| ID | Requirement | Priority |
|---|---|---|
| L-01 | The system shall use Groq API (free tier) as the primary LLM provider | Must |
| L-02 | The system shall support mixtral-8x7b-32768 as the default model | Must |
| L-03 | The system shall use a system prompt that instructs the LLM to reason only from provided graph context and not to invent relationships | Must |
| L-04 | The system shall record LLM response latency separately from graph traversal latency | Must |
| L-05 | The system shall handle Groq API rate limits gracefully with exponential backoff | Should |

### 2.6 Evaluation Layer Requirements

| ID | Requirement | Priority |
|---|---|---|
| E-01 | The system shall display a Streamlit dashboard with side-by-side comparison of baseline and GraphRAG pipelines | Must |
| E-02 | The dashboard shall show per-query: tokens used, latency, cost, accuracy, hallucination count for both pipelines | Must |
| E-03 | The dashboard shall show aggregate metrics across all benchmark runs: average token reduction %, average cost reduction %, hallucination rate | Must |
| E-04 | The dashboard shall render the GraphRAG causal subgraph as an interactive network visualization (pyvis) | Must |
| E-05 | The dashboard shall include a "Fire Synthetic Incident" button that triggers a new benchmark run and updates all metrics in real time | Must |
| E-06 | The dashboard shall show the benchmark dataset's ground truth RCA alongside each pipeline's answer, with a match/no-match indicator | Must |

### 2.7 TEE Requirements

| ID | Requirement | Priority |
|---|---|---|
| T-01 | The inference orchestration layer shall run inside a Gramine-SGX enclave (simulation mode for hackathon) | Must |
| T-02 | The system shall generate an attestation report on startup containing the MRENCLAVE measurement | Must |
| T-03 | The system shall expose a `GET /attest` endpoint that returns the current enclave measurement and attestation timestamp | Must |
| T-04 | Incident data shall be decrypted only inside the enclave, never in plaintext outside | Must |
| T-05 | The system shall use a derived sealing key for data decryption; no key material shall be stored in plaintext on disk | Must |
| T-06 | The Streamlit dashboard shall display TEE status: enclave active, MRENCLAVE hash (truncated), and last attestation verification timestamp | Must |
| T-07 | All communication between the enclave and external services (TigerGraph, Groq) shall use TLS | Must |
| T-08 | The system shall document the production path to AWS Nitro Enclaves in architecture.md | Should |

### 2.8 Data Requirements

| ID | Requirement | Priority |
|---|---|---|
| D-01 | The system shall include a Python script `generate_incidents.py` that creates a synthetic incident dataset with known ground truth | Must |
| D-02 | The synthetic dataset shall contain at least 25 distinct incidents with varying hop depths (2-hop, 4-hop, 6-hop causal chains) | Must |
| D-03 | Each synthetic incident shall specify: alert_id, affected service, root cause ConfigChange, affected downstream services, and expected unpaged teams | Must |
| D-04 | The system shall include a `load_graph.py` script that loads the synthetic dataset into TigerGraph Cloud | Must |

---

## 3. Non-Functional Requirements

### 3.1 Performance Requirements

| ID | Requirement | Target |
|---|---|---|
| NF-P-01 | GraphRAG pipeline end-to-end latency (graph query + LLM call) | < 2,000ms |
| NF-P-02 | Baseline pipeline end-to-end latency | No target (expected slower) |
| NF-P-03 | Token count: GraphRAG pipeline context | < 600 tokens |
| NF-P-04 | Token count: Baseline pipeline context | > 8,000 tokens |
| NF-P-05 | Token reduction: GraphRAG vs baseline | > 85% |
| NF-P-06 | Graph traversal latency (GSQL only) | < 200ms |
| NF-P-07 | Dashboard refresh after incident fire | < 5 seconds |

### 3.2 Accuracy Requirements

| ID | Requirement | Target |
|---|---|---|
| NF-A-01 | GraphRAG root cause identification accuracy (vs ground truth) | > 90% |
| NF-A-02 | Baseline root cause identification accuracy (vs ground truth) | Expected < 60% |
| NF-A-03 | GraphRAG unpaged team detection rate | 100% (graph is exhaustive) |
| NF-A-04 | Baseline unpaged team detection rate | Expected < 50% |
| NF-A-05 | GraphRAG hallucination rate (entities not in subgraph) | < 5% |
| NF-A-06 | Baseline hallucination rate | Expected > 20% |

### 3.3 Security Requirements

| ID | Requirement |
|---|---|
| NF-S-01 | No incident data (service names, config values, team info) shall be logged outside the enclave |
| NF-S-02 | The MRENCLAVE measurement shall be reproducible: same code → same hash |
| NF-S-03 | API keys (Groq, TigerGraph) shall be loaded inside the enclave from environment variables, never hardcoded |
| NF-S-04 | The system shall not store raw incident payloads on disk outside the enclave |
| NF-S-05 | TLS certificate validation shall be enabled for all external API calls |

### 3.4 Cost Requirements

| ID | Requirement |
|---|---|
| NF-C-01 | Total infrastructure cost shall be ₹0 (free tiers only) |
| NF-C-02 | LLM cost per query shall be demonstrably lower for GraphRAG pipeline than baseline |
| NF-C-03 | The system shall display estimated cost per query using current Groq pricing |

### 3.5 Usability Requirements

| ID | Requirement |
|---|---|
| NF-U-01 | Any developer with Python 3.10+ can run the full stack locally following the README |
| NF-U-02 | The dashboard shall be self-explanatory to a non-technical judge within 30 seconds |
| NF-U-03 | A new benchmark run shall be triggerable with a single button click |

---

## 4. Hackathon-Specific Requirements

These requirements are derived directly from the hackathon judging criteria.

| Judging Criterion | PostMortemIQ Requirement |
|---|---|
| Proves tokens reduced | Display per-query and aggregate token counts; benchmark across 25 incidents |
| Proves cost reduced | Display per-query cost in USD; show aggregate savings |
| Proves speed improved | Display end-to-end latency for both pipelines |
| Proves accuracy improved | Compare pipeline output against synthetic ground truth; show F1 score |
| 4-layer AI Factory architecture | Each of the 4 layers must be a distinct, separately documented module |
| Working product | All components must run end-to-end without manual intervention |
| Comparison dashboard | Streamlit dashboard must be the primary interface and show all metrics |
| Graph + LLM integration | GSQL traversal must feed directly into LLM prompt construction |
| Novelty | TEE integration + incident RCA domain = no existing comparable project |
| Demo video ready | System must demonstrate a complete incident → RCA cycle in under 3 minutes |

---

## 5. Out of Scope

The following are explicitly out of scope for the hackathon submission:

- Real production incident data (synthetic data only)
- Full SGX hardware attestation (simulation mode sufficient for demo)
- Multi-tenant support
- User authentication and authorization
- Production-grade key management (AWS KMS, HashiCorp Vault)
- Real-time alert ingestion from live monitoring systems (Prometheus, Datadog)
- Auto-remediation (this system identifies root cause only, does not fix it)
- Model fine-tuning

---

## 6. Constraints

| Constraint | Impact |
|---|---|
| TigerGraph Cloud free tier: 50GB storage | Dataset must remain synthetic and small (< 1GB) |
| Groq free tier: 14,400 requests/day | Benchmark suite limited to 25 incidents with 2 pipeline calls each = 50 requests per run |
| No SGX hardware | TEE runs in Gramine simulation mode; real hardware isolation not demonstrated |
| No paid cloud services | AWS Nitro is documented as production path, not implemented |
| Solo developer, 2-week timeline | Scope constrained to the 25-incident benchmark; no real-time ingestion |

---

## 7. Acceptance Criteria

The project is ready for submission when all of the following are true:

- [ ] TigerGraph graph loads successfully with synthetic incident dataset
- [ ] GSQL `blast_radius` query returns correct results in < 200ms
- [ ] GSQL `root_cause_chain` query identifies correct root cause for all 25 test incidents
- [ ] Baseline pipeline context exceeds 8,000 tokens for all test incidents
- [ ] GraphRAG pipeline context stays below 600 tokens for all test incidents
- [ ] Token reduction across benchmark run exceeds 85%
- [ ] GraphRAG accuracy on synthetic ground truth exceeds 90%
- [ ] Baseline hallucination rate measurably higher than GraphRAG (minimum 10% difference)
- [ ] Streamlit dashboard displays all metrics correctly
- [ ] TEE enclave starts without errors in simulation mode
- [ ] Attestation endpoint returns valid MRENCLAVE measurement
- [ ] Dashboard shows TEE active status
- [ ] README contains complete setup instructions runnable in < 30 minutes
- [ ] All components run for ₹0 cost
- [ ] 3-minute demo video recorded showing complete incident-to-RCA cycle

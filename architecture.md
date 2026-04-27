# PostMortemIQ — System Architecture
### GraphRAG Incident Root-Cause Engine with Trusted Execution Environment

---

## 1. Overview

PostMortemIQ is a production incident root-cause analysis (RCA) system built on a 4-layer AI Factory architecture. It combines TigerGraph's multi-hop graph traversal with LLM inference to trace causal chains across alerts, services, deployments, and config changes — in milliseconds, at a fraction of the token cost of baseline LLM approaches.

The Trusted Execution Environment (TEE) layer wraps the entire inference pipeline, ensuring that sensitive production incident data — service names, config values, secrets leaked via environment variables, team structures — is processed inside a cryptographically isolated enclave. Neither the cloud provider, the infrastructure operator, nor any third party can observe the data being reasoned over.

---

## 2. System Layers (AI Factory Model)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRUSTED EXECUTION ENVIRONMENT                     │
│              (Gramine-SGX Enclave / AWS Nitro Enclave)              │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │               LAYER 4 — EVALUATION LAYER                    │    │
│  │   Streamlit Dashboard · Benchmark Engine · Metric Store     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ▲                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                LAYER 3 — LLM LAYER                          │    │
│  │   Groq API (encrypted transport) · Prompt Builder          │    │
│  │   Secure Context Assembly · Response Verifier              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ▲                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │         LAYER 2 — INFERENCE ORCHESTRATION LAYER             │    │
│  │   Incident Router · Pipeline Controller · Cost Tracker     │    │
│  │   Baseline Dispatcher · GraphRAG Dispatcher · Comparator   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ▲                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │               LAYER 1 — GRAPH LAYER                         │    │
│  │   TigerGraph Cloud · GSQL Traversal Engine                 │    │
│  │   Entity Graph · Causal Chain Queries · Schema Manager     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
├───────────────────────────────────────────────────────────────────── │
│              TEE SECURITY SERVICES (horizontal)                      │
│   Attestation Service · Key Manager · Audit Logger · Seal/Unseal    │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
               ┌──────────────┴──────────────┐
               │     INCIDENT DATA SOURCES    │
               │  Raw Logs · Alerts · Deploys │
               │  Config Diffs · Runbooks     │
               └─────────────────────────────┘
```

---

## 3. Component Architecture

### 3.1 Layer 1 — Graph Layer

**TigerGraph Cloud (Free Tier)**

| Component | Role |
|---|---|
| `IncidentGraph` schema | Defines vertex and edge types for the causal graph |
| `AlertVertex` | Represents a fired monitoring alert with severity and timestamp |
| `ServiceVertex` | Represents a microservice with owner, SLA tier, and language |
| `DeploymentVertex` | Represents a deployment event with version and diff summary |
| `ConfigChangeVertex` | Represents a config mutation with before/after values |
| `TeamVertex` | Represents an on-call team with escalation path |
| `RunbookVertex` | Represents a remediation playbook |
| GSQL traversal engine | Executes multi-hop causal chain queries |

**Graph Schema:**
```
Alert ──fired_on──► Service ──had_deployment──► Deployment
                       │                              │
                  owned_by                     changed_config
                       │                              │
                      Team                     ConfigChange
                       │                              │
                  has_runbook               broke_dependency
                       │                              │
                    Runbook                      Dependency
                                                      │
                                                 used_by
                                                      │
                                               Service (B,C,D...)
```

**Key GSQL Queries:**
- `blast_radius(incident_id, max_hops)` — finds all affected services N hops from alert origin
- `root_cause_chain(alert_id)` — traces backwards from alert to earliest causal ConfigChange
- `unpaged_teams(incident_id)` — finds teams owning affected services not yet in the alert group
- `runbook_matcher(service_id, issue_type)` — finds the best matching remediation runbook

---

### 3.2 Layer 2 — Inference Orchestration Layer

**FastAPI service running inside the enclave**

```
IncomingIncident
      │
      ▼
IncidentRouter
      │
      ├──────────────────────────────────┐
      │                                  │
      ▼                                  ▼
BaselineDispatcher               GraphRAGDispatcher
      │                                  │
      │  Build full raw context           │  Run GSQL traversal
      │  (logs + alerts + docs)           │  Build minimal subgraph
      │                                  │
      ▼                                  ▼
 LLM Layer                          LLM Layer
(large context)                  (small context)
      │                                  │
      └──────────────┬───────────────────┘
                     │
                     ▼
              Comparator Engine
                     │
              MetricsCollector
                     │
              EvaluationLayer
```

**Key modules:**
- `incident_router.py` — parses incoming incident JSON, extracts entity IDs
- `baseline_pipeline.py` — assembles raw log + alert dump, calls LLM with full context
- `graphrag_pipeline.py` — calls TigerGraph GSQL, assembles subgraph context, calls LLM
- `comparator.py` — runs both pipelines in parallel, collects token/latency/accuracy metrics
- `cost_tracker.py` — calculates per-query cost using `tiktoken` and model pricing

---

### 3.3 Layer 3 — LLM Layer

**Groq API (free tier) inside encrypted transport**

```
SubgraphContext (380 tokens)
        │
        ▼
  PromptBuilder
  ┌──────────────────────────────────────┐
  │  System: "You are an SRE analyzing  │
  │  a verified causal graph subgraph.  │
  │  Do not invent relationships."      │
  │                                      │
  │  Graph Context:                      │
  │    Alert A → Service auth-svc       │
  │    Deployment v2.4.1 at 14:32 UTC   │
  │    ConfigChange: JWT_EXPIRY 3600→60 │
  │    Broke: payment-svc dependency    │
  │    Team Payments: NOT PAGED         │
  │                                      │
  │  Question: What is the root cause?  │
  └──────────────────────────────────────┘
        │
        ▼
  Groq API (mixtral-8x7b / llama-3)
        │
        ▼
  RCA Report + Confidence Score
        │
        ▼
  ResponseVerifier
  (checks response doesn't hallucinate
   entities not in the subgraph)
```

---

### 3.4 Layer 4 — Evaluation Layer

**Streamlit Dashboard**

- Side-by-side: Baseline LLM result vs GraphRAG result
- Live metrics per query: tokens used, latency (ms), cost (USD), accuracy score
- Running aggregate: total token savings %, average cost reduction, hallucination rate
- Graph visualization: `pyvis` rendering of the traversed causal subgraph
- Benchmark mode: run all 25 synthetic incidents and display aggregate scorecard

---

## 4. TEE Integration Architecture

### 4.1 Why TEE for PostMortemIQ

Production incident data is among the most sensitive data in any organization:
- Service names reveal infrastructure topology (attack surface)
- Config change diffs may expose API keys, passwords, and secrets
- Team structures reveal organizational hierarchy
- Deployment history reveals release cadence and vulnerability windows

Without TEE, sending this data to an LLM API or cloud graph database creates an unacceptable data exposure risk. With TEE, the entire inference pipeline executes inside a hardware-isolated enclave that guarantees:
1. **Confidentiality** — even the cloud provider cannot read the data
2. **Integrity** — the code running inside is cryptographically verified
3. **Attestation** — any party can verify that the correct, unmodified code processed the data

### 4.2 TEE Technology Stack

**Primary: Gramine + Intel SGX (simulation mode for hackathon)**
- Gramine is an open-source library OS that runs unmodified Linux applications inside Intel SGX enclaves
- Simulation mode (`SGX=1 SGX_DEBUG=1`) runs on any x86 machine without SGX hardware
- Allows full demo without cloud cost

**Production path: AWS Nitro Enclaves**
- Isolated EC2 sub-environment with no persistent storage, no interactive access
- Supports Python applications via Nitro Enclaves SDK
- Free tier: m5.xlarge (first 750 hours free)

### 4.3 TEE Data Flow

```
OUTSIDE ENCLAVE                    INSIDE ENCLAVE (TEE)
─────────────────                  ──────────────────────────────────────

Raw Incident JSON                  
(encrypted at rest)
        │
        │ ── TLS + Attestation ──►  Attestation Verifier
        │                                │
        │                           Key Manager (unseals decryption key)
        │                                │
        │                           Incident Decryptor
        │                                │
        │                           IncidentRouter
        │                                │
        │                    ┌──────────┴──────────┐
        │                    │                     │
        │               BaselinePipeline    GraphRAGPipeline
        │                    │                     │
        │               [raw logs →          [GSQL traversal →
        │                LLM call]            subgraph → LLM call]
        │                    │                     │
        │               Comparator ◄──────────────┘
        │                    │
        │               MetricsStore (sealed inside enclave)
        │                    │
        │ ◄── Encrypted ──── RCA Report + Benchmark Data
        │
Streamlit Dashboard
(decrypts with user key,
 displays results)
```

### 4.4 Attestation Flow

```
Client                    Enclave                   Intel IAS / AWS
   │                         │                           │
   │── Request attestation ──►│                           │
   │                         │── Generate quote ─────────►│
   │                         │                           │── Verify SGX ──┐
   │                         │                           │◄── Report ─────┘
   │◄── Signed attestation ──│◄── Verification report ───│
   │                         │
   │ [Client verifies:        │
   │  - Correct code hash     │
   │  - Unmodified enclave    │
   │  - Known-good TCB]       │
   │                         │
   │── Send encrypted data ──►│
   │                         │ [Process inside enclave]
   │◄── Encrypted result ────│
```

---

## 5. Data Flow — End to End

```
Step 1: Incident fires
  └─ AlertManager → POST /incident {alert_id, service_id, timestamp}

Step 2: Enclave receives encrypted payload
  └─ TEE decrypts using sealed key
  └─ AttestationVerifier confirms enclave integrity

Step 3: Orchestration layer routes the incident
  └─ IncidentRouter extracts entity IDs
  └─ Launches baseline and GraphRAG pipelines in parallel

Step 4a: Baseline pipeline
  └─ Fetches raw logs (mock: ~8,000 tokens)
  └─ Fetches alert descriptions (~2,000 tokens)
  └─ Fetches deployment notes (~1,500 tokens)
  └─ Sends ~11,500-token prompt to Groq
  └─ Records: tokens=11,500, latency=Xms, cost=$Y

Step 4b: GraphRAG pipeline
  └─ Sends GSQL blast_radius query to TigerGraph
  └─ Receives causal subgraph (15 nodes, 22 edges)
  └─ PromptBuilder assembles ~380-token prompt
  └─ Sends 380-token prompt to Groq
  └─ Records: tokens=380, latency=Xms, cost=$Y

Step 5: Comparator aggregates
  └─ Token delta, latency delta, cost delta
  └─ Accuracy check vs ground truth RCA
  └─ Hallucination check (did LLM invent graph nodes?)

Step 6: Results sealed and returned
  └─ RCA report encrypted with user public key
  └─ Attestation report appended
  └─ Metrics written to benchmark store

Step 7: Dashboard renders
  └─ Streamlit decrypts and displays
  └─ Side-by-side comparison updated
  └─ Running totals updated
```

---

## 6. Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│              Developer Machine / CI              │
│  ┌─────────────────┐    ┌───────────────────┐   │
│  │  Streamlit UI   │    │  Data Generator   │   │
│  │  (port 8501)    │    │  (synthetic       │   │
│  └────────┬────────┘    │   incidents)      │   │
│           │             └───────────────────┘   │
│           │ HTTPS                               │
│  ┌────────▼────────────────────────────────┐    │
│  │         FastAPI Orchestration           │    │
│  │         (Gramine SGX simulation)        │    │
│  │         (port 8000)                     │    │
│  └────────┬──────────────┬────────────────┘    │
│           │              │                      │
└───────────┼──────────────┼──────────────────────┘
            │              │
            ▼              ▼
   TigerGraph Cloud    Groq API
   (free tier)         (free tier)
   GSQL queries        LLM inference
```

---

## 7. Technology Stack Summary

| Component | Technology | Cost |
|---|---|---|
| Graph database | TigerGraph Cloud (free tier) | ₹0 |
| Graph queries | GSQL | ₹0 |
| TEE runtime | Gramine + SGX simulation | ₹0 |
| TEE attestation (demo) | Gramine RA-TLS | ₹0 |
| LLM inference | Groq API free tier | ₹0 |
| Orchestration | FastAPI + Python | ₹0 |
| Dashboard | Streamlit Community Cloud | ₹0 |
| Token counting | tiktoken | ₹0 |
| Graph visualization | pyvis | ₹0 |
| Synthetic data | faker + Python | ₹0 |
| Encryption | Python cryptography library | ₹0 |
| Attestation verification | Gramine RA-TLS / simulated | ₹0 |

**Total cost: ₹0**

---

## 8. Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| TEE runtime for hackathon | Gramine simulation mode | No SGX hardware required; full architecture demonstrated |
| Graph DB | TigerGraph Cloud | Free tier, native GSQL, best multi-hop performance |
| LLM provider | Groq | Fastest free inference; 14,400 req/day |
| Data format | Synthetic JSON incidents | Full ground truth control for accurate benchmarking |
| Parallel pipelines | Both run on every query | Clean side-by-side comparison for dashboard |
| Attestation | RA-TLS simulated | Shows the concept without hardware dependency |

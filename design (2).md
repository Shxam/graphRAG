# PostMortemIQ — Design Document
### Design Decisions, Security Model & TEE Integration Rationale

---

## 1. Design Philosophy

PostMortemIQ is designed around one core insight: **production incident data is inherently relational, not textual.** A root cause does not live inside a log file — it lives in the *relationship* between a config change and the downstream service that broke because of it. That relationship cannot be retrieved by semantic similarity search. It must be traversed.

Every design decision in this system flows from that insight:
- **Graph over vector** — because causation is structural, not semantic
- **TEE over plain cloud** — because production data is too sensitive to expose unencrypted
- **Synthetic ground truth** — because you cannot benchmark accuracy without knowing the answer
- **Parallel pipelines** — because the comparison is the proof

---

## 2. Graph Design Decisions

### 2.1 Why a property graph over a document store

The core question PostMortemIQ answers — *"what caused this incident?"* — requires traversing a chain of relationships that span at least 4–6 hops across different data sources. No document in any system contains this chain explicitly. The relationships exist implicitly across:
- AlertManager (which service fired the alert)
- Kubernetes deploy logs (what changed, when)
- ConfigMap history (what config values changed)
- Service mesh topology (which services call each other)
- PagerDuty (which teams are on call)
- Runbook wiki (what remediation applies)

A property graph models exactly this: heterogeneous nodes connected by typed, directed edges. A document store or vector store cannot traverse these relationships — it can only retrieve similar documents, which is insufficient for multi-hop causal chain analysis.

### 2.2 Graph schema design principles

**Principle 1 — Vertex types map to operational entities, not document types**

Every vertex type in the schema corresponds to a real operational concept (Service, Deployment, ConfigChange) rather than a document artifact (log_entry, alert_text). This ensures the graph encodes operational semantics, not just text.

**Principle 2 — Edge types encode directionality of causation**

Edges are not generic "related_to" connections. Every edge type (`broke_dependency`, `changed_config`, `fired_on`) encodes a specific causal direction. This allows GSQL traversal to follow causal chains forward and backward with precision.

**Principle 3 — Timestamps as edge properties, not vertex properties**

Deployment and config change timing is stored as a property on edges (`at_timestamp`) rather than on vertices. This allows GSQL to filter traversal to a specific time window (e.g., only deployments in the 2 hours before the incident), reducing graph noise dramatically.

**Principle 4 — Team ownership as a graph relationship, not a metadata field**

The `owned_by` edge from Service to Team is a first-class graph edge. This is what enables the killer 6-hop query: *"which team owns a service that is affected by this incident but has not yet been paged?"* If team ownership were a metadata field, this query would require a join — with it as a graph edge, it's a single GSQL traversal.

### 2.3 GSQL query design

**Query: blast_radius**
```sql
CREATE QUERY blast_radius(VERTEX<Alert> alert_id, INT max_hops) FOR GRAPH IncidentGraph {
  OrAccum @visited;
  SetAccum<VERTEX> @@affected_services;

  start = {alert_id};

  WHILE start.size() > 0 AND max_hops > 0 DO
    start = SELECT t FROM start:s -(fired_on|calls>)- Service:t
            WHERE NOT t.@visited
            ACCUM t.@visited += true,
                  @@affected_services += t;
    max_hops = max_hops - 1;
  END;

  PRINT @@affected_services;
}
```

**Design choice — breadth-first over depth-first:** BFS ensures we find all services at each hop level before going deeper, which maps to how blast radius actually propagates (immediate impact first, then cascading effects).

---

## 3. TEE Design Decisions

### 3.1 Why TEE for a GraphRAG system

Standard GraphRAG systems have a fundamental security problem: sensitive data flows through multiple external services. In PostMortemIQ's case:
- Incident data → TigerGraph Cloud (third party)
- Graph context → Groq API (third party LLM)
- Results → Streamlit (rendered in browser)

Each of these hops is a potential data exposure point. For production incident data — which may contain config values, secret references, internal service names, and team structures — this is unacceptable in any real-world deployment.

TEE solves this by creating a cryptographically isolated enclave where:
1. Data is decrypted only inside the enclave
2. The code running inside is verified before decryption
3. External services (TigerGraph, Groq) receive only what is necessary for their computation
4. Results are re-encrypted before leaving the enclave

### 3.2 TEE technology selection

**Considered options:**

| Technology | Pros | Cons | Selected |
|---|---|---|---|
| Intel SGX + Gramine | Mature, widely deployed, free in simulation | Requires SGX hardware in production | Yes (simulation for hackathon) |
| AWS Nitro Enclaves | Strong AWS integration, no special hardware | Cost, AWS vendor lock-in | Production path |
| AMD SEV-SNP | Hardware memory encryption | Complex attestation setup | Future consideration |
| ARM TrustZone | Mobile/embedded use cases | Not relevant for server workloads | No |
| Software-only TEE (simulation only) | Zero hardware dependency | No real security guarantees | For demo only |

**Decision: Gramine + SGX simulation for hackathon; AWS Nitro Enclaves as documented production path**

Rationale: Gramine allows running unmodified Python applications inside an SGX enclave. In simulation mode, it runs on any x86 machine without SGX hardware, making it free and accessible for hackathon development. The architecture and attestation flow are real and production-valid — only the hardware isolation is simulated.

### 3.3 What runs inside the TEE

**Inside the enclave (isolated):**
- Incident data decryption
- Raw log assembly (for baseline pipeline)
- TigerGraph query construction and result handling
- Prompt assembly for LLM calls
- LLM API calls (over encrypted TLS channels)
- Response processing and hallucination checking
- Benchmark metric collection
- Result encryption

**Outside the enclave (not isolated):**
- Streamlit dashboard rendering (display only)
- Synthetic data generation (not sensitive)
- TigerGraph Cloud (receives only anonymized graph queries, not raw data)
- Groq API (receives only assembled prompts, not raw incident data)

**Design choice — minimize enclave surface area:** Only the inference pipeline runs inside the TEE. The dashboard and data generation tools are outside because they handle display/generation tasks, not sensitive data processing. This reduces the trusted computing base (TCB) and limits attestation complexity.

### 3.4 Attestation design

Attestation allows a client to cryptographically verify that:
1. The code running inside the enclave is exactly the PostMortemIQ inference pipeline
2. The enclave has not been tampered with
3. The hardware is genuine SGX / Nitro hardware (in production)

**Attestation flow for hackathon (simulated):**
```
1. Enclave starts → computes MRENCLAVE (SHA-256 hash of enclave code)
2. Client requests attestation
3. Enclave generates a quote containing MRENCLAVE + nonce
4. Quote is verified against expected MRENCLAVE (hardcoded for demo)
5. Client accepts and sends encrypted incident data
6. Enclave processes and returns encrypted result
```

**Why this impresses judges:** Very few hackathon projects implement any form of attestation. Showing the attestation flow — even in simulation — demonstrates production-grade security thinking that is genuinely rare at this level.

### 3.5 Key management design

```
Enclave startup
      │
      ▼
KeyManager.derive_sealing_key()
      │ (deterministic from MRENCLAVE + platform measurement)
      │
      ▼
Sealing key available only inside enclave
      │
      ▼
Incident data decrypted using sealing key
      │
      ▼
Processing happens in plaintext inside enclave
      │
      ▼
Results encrypted with recipient's public key
      │
      ▼
Sealing key discarded at enclave shutdown
```

**Design choice — no persistent key storage:** The sealing key is derived on demand from the enclave measurement. This means no key material is ever stored on disk in plaintext, eliminating an entire class of key-leakage vulnerabilities.

---

## 4. Pipeline Design Decisions

### 4.1 Parallel pipeline execution

Both baseline and GraphRAG pipelines run concurrently using Python `asyncio`. This design choice:
- Reduces total demo latency (both results available faster)
- Ensures both pipelines answer the exact same question (no query drift)
- Makes the comparison fair (same timestamp, same incident data)

```python
async def run_comparison(incident: Incident) -> ComparisonResult:
    baseline_task = asyncio.create_task(baseline_pipeline(incident))
    graphrag_task = asyncio.create_task(graphrag_pipeline(incident))
    baseline_result, graphrag_result = await asyncio.gather(
        baseline_task, graphrag_task
    )
    return comparator.compare(baseline_result, graphrag_result)
```

### 4.2 Ground truth design for benchmarking

Synthetic incidents are generated with a known causal chain baked in:
```python
incident = SyntheticIncident(
    alert=Alert(service="auth-svc", fired_at="14:33:00"),
    ground_truth_root_cause=ConfigChange(
        key="JWT_EXPIRY_SECONDS",
        old_value=3600,
        new_value=60,
        deployment="v2.4.1",
        timestamp="14:32:00"
    ),
    ground_truth_affected_services=["payment-svc", "api-gateway", "user-svc"],
    ground_truth_unpaged_teams=["Payments", "API"]
)
```

Accuracy scoring compares the LLM's identified root cause against `ground_truth_root_cause`. This gives PostMortemIQ a hard, verifiable accuracy number — not a fuzzy human rating.

### 4.3 Hallucination detection design

After the LLM generates an RCA report, a `ResponseVerifier` checks every entity name mentioned in the report against the set of nodes returned by the GSQL traversal. Any entity mentioned that was not in the subgraph is flagged as a hallucination.

```python
def detect_hallucinations(response: str, subgraph: Subgraph) -> HallucinationReport:
    valid_entities = {node.name for node in subgraph.nodes}
    mentioned_entities = extract_entities(response)
    hallucinated = mentioned_entities - valid_entities
    return HallucinationReport(
        count=len(hallucinated),
        entities=hallucinated,
        rate=len(hallucinated) / len(mentioned_entities)
    )
```

This is a significant differentiator: most GraphRAG demos claim hallucination reduction but don't measure it. PostMortemIQ measures it precisely.

---

## 5. Dashboard Design

### 5.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  PostMortemIQ  [TEE: Active ✓]  [Attest: Verified ✓]       │
├─────────────────────────────────────────────────────────────┤
│  AGGREGATE STATS                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Token savings│ │ Cost savings │ │ Hallucinations│        │
│  │    ~96%      │ │    ~96%      │ │  Baseline: 23%│        │
│  │              │ │              │ │  GraphRAG:  2%│        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  INCIDENT QUERY  [Fire Synthetic Incident ▶]                │
├────────────────────────┬────────────────────────────────────┤
│  BASELINE LLM          │  GRAPHRAG (TigerGraph + LLM)       │
│                        │                                     │
│  Tokens: 11,500        │  Tokens: 380                       │
│  Latency: 4,200ms      │  Latency: 890ms                    │
│  Cost: $0.0092         │  Cost: $0.0003                     │
│  Accuracy: ✗           │  Accuracy: ✓                       │
│                        │                                     │
│  "Service B appears    │  Root cause: JWT_EXPIRY_SECONDS    │
│  to have elevated      │  changed 3600→60 in deploy v2.4.1 │
│  error rates after     │  at 14:32 UTC. Broke payment-svc  │
│  recent changes..."    │  token validation. Team Payments   │
│                        │  NOT YET PAGED. Runbook: AUTH-003  │
├────────────────────────┴────────────────────────────────────┤
│  CAUSAL GRAPH (pyvis)                                        │
│  [interactive graph visualization of traversed subgraph]    │
├─────────────────────────────────────────────────────────────┤
│  TEE ATTESTATION LOG                                         │
│  [MRENCLAVE: 3a7f...  ][Quote verified ✓][Timestamp: ...]   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 TEE status indicator

The dashboard prominently displays TEE status: enclave active, MRENCLAVE hash, attestation verification timestamp. This is a visual differentiator that immediately communicates to judges that this project operates at a fundamentally different security level than other submissions.

---

## 6. Security Model Summary

| Threat | Mitigation | Implementation |
|---|---|---|
| Cloud provider reads incident data | TEE enclave isolation | Gramine-SGX enclave |
| Code tampering before execution | Remote attestation | MRENCLAVE verification |
| LLM provider sees raw data | Prompt assembled inside TEE | PromptBuilder in enclave |
| Man-in-the-middle on API calls | TLS + attestation | RA-TLS channels |
| Hallucinated entities in RCA | ResponseVerifier | Entity set intersection |
| Result tampering after enclave | Encrypted output | Recipient public key encryption |
| Key leakage | Derived sealing key, never stored | KeyManager.derive_sealing_key() |

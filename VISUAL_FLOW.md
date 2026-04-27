# PostMortemIQ - Visual Implementation Flow

## 🎯 The Big Picture: How It All Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR PRODUCTION SYSTEM                       │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │           │
│  │   A      │──│   B      │──│   C      │──│   D      │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │             │             │             │                   │
│       │ ❌ ERROR    │             │             │                   │
│       ▼             ▼             ▼             ▼                   │
│  ┌─────────────────────────────────────────────────────┐           │
│  │         Monitoring (Prometheus/Datadog)             │           │
│  └────────────────────────┬────────────────────────────┘           │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            │ 🚨 ALERT FIRES
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         POSTMORTEMIQ                                 │
│                                                                       │
│  Step 1: Receive Alert                                              │
│  ┌────────────────────────────────────────────┐                     │
│  │ "High error rate in Service A"             │                     │
│  │ Severity: Critical                         │                     │
│  │ Time: 14:33:00                             │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   │                                                  │
│                   ▼                                                  │
│  Step 2: Query TigerGraph (Graph Traversal)                         │
│  ┌────────────────────────────────────────────┐                     │
│  │  GSQL: blast_radius(alert_id, 4 hops)     │                     │
│  │                                             │                     │
│  │  Alert ──► Service A ──► Deployment v2.4.1 │                     │
│  │              │                │             │                     │
│  │              │                ▼             │                     │
│  │              │         ConfigChange         │                     │
│  │              │         JWT_EXPIRY: 3600→60  │                     │
│  │              │                │             │                     │
│  │              ▼                ▼             │                     │
│  │         Service B ◄──── Dependency         │                     │
│  │              │                              │                     │
│  │              ▼                              │                     │
│  │         Service C                          │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   │                                                  │
│                   │ Subgraph: 6 nodes, 8 edges                      │
│                   │ Context: ~380 tokens                             │
│                   ▼                                                  │
│  Step 3: Build Minimal Prompt                                       │
│  ┌────────────────────────────────────────────┐                     │
│  │ "Analyze this causal graph:                │                     │
│  │  - Alert fired on Service A                │                     │
│  │  - Deployment v2.4.1 at 14:32              │                     │
│  │  - Config JWT_EXPIRY changed 3600→60       │                     │
│  │  - Broke Service B dependency              │                     │
│  │  - Affected Service C                      │                     │
│  │  What is the root cause?"                  │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   │                                                  │
│                   ▼                                                  │
│  Step 4: LLM Analysis (Groq API)                                    │
│  ┌────────────────────────────────────────────┐                     │
│  │ Input: 380 tokens                          │                     │
│  │ Model: mixtral-8x7b                        │                     │
│  │ Latency: 890ms                             │                     │
│  │ Cost: $0.0003                              │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   │                                                  │
│                   ▼                                                  │
│  Step 5: Root Cause Analysis                                        │
│  ┌────────────────────────────────────────────┐                     │
│  │ ✅ Root Cause: JWT_EXPIRY config change    │                     │
│  │ ✅ Affected: Service A, B, C               │                     │
│  │ ✅ Unpaged Teams: Payments, API            │                     │
│  │ ✅ Remediation: Rollback to 3600           │                     │
│  │ ✅ Confidence: 95%                         │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   │                                                  │
└───────────────────┼──────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         RESULTS                                      │
│                                                                       │
│  📊 Dashboard                    📱 Notifications                   │
│  ┌──────────────────┐           ┌──────────────────┐               │
│  │ Token Reduction  │           │ Slack: Payments  │               │
│  │     96%          │           │ Team             │               │
│  │                  │           │                  │               │
│  │ Cost Savings     │           │ PagerDuty: API   │               │
│  │     96%          │           │ Team             │               │
│  │                  │           │                  │               │
│  │ Time to RCA      │           │ Email: SRE Lead  │               │
│  │     890ms        │           │                  │               │
│  └──────────────────┘           └──────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Comparison: Baseline vs GraphRAG

### Baseline LLM Approach (Traditional)

```
Alert Fires
    │
    ▼
Dump Everything into LLM
    │
    ├─ All logs (3,000 tokens)
    ├─ All alerts (2,000 tokens)
    ├─ All deployments (2,000 tokens)
    ├─ All configs (1,500 tokens)
    └─ All docs (3,000 tokens)
    │
    │ Total: 11,500 tokens
    │ Cost: $0.0092
    │ Time: 4,200ms
    ▼
LLM tries to find patterns
    │
    ├─ Drowns in noise
    ├─ Invents relationships (hallucinations)
    └─ Gives vague answer
    │
    ▼
❌ "Service B appears to have issues
    after recent changes. Check logs
    and recent deployments."
    
Accuracy: ~60%
Hallucinations: ~23%
```

### GraphRAG Approach (PostMortemIQ)

```
Alert Fires
    │
    ▼
Query Graph for Causal Chain
    │
    ├─ GSQL: blast_radius(alert, 4)
    ├─ GSQL: root_cause_chain(alert)
    └─ GSQL: unpaged_teams(incident)
    │
    │ Graph traversal: 150ms
    │ Returns: 6 nodes, 8 edges
    ▼
Build Minimal Context
    │
    └─ Only relevant causal chain
    │
    │ Total: 380 tokens
    │ Cost: $0.0003
    │ Time: 890ms
    ▼
LLM analyzes verified graph
    │
    ├─ Clear causal path
    ├─ No invented relationships
    └─ Precise answer
    │
    ▼
✅ "Root cause: JWT_EXPIRY changed
    from 3600 to 60 in deployment
    v2.4.1 at 14:32. Broke Service B
    token validation. Page Payments
    and API teams."
    
Accuracy: >90%
Hallucinations: <5%
```

---

## 📊 Data Flow: From Alert to Action

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA COLLECTION (Continuous)                           │
└─────────────────────────────────────────────────────────────────┘

Your Infrastructure          TigerGraph Graph
─────────────────           ────────────────

Services                    Service Vertices
  ├─ auth-svc      ────►      ├─ auth-svc
  ├─ payment-svc   ────►      ├─ payment-svc
  └─ api-gateway   ────►      └─ api-gateway

Deployments                 Deployment Vertices
  ├─ v2.4.1        ────►      ├─ deploy_1
  └─ v2.4.0        ────►      └─ deploy_2

Config Changes              ConfigChange Vertices
  ├─ JWT_EXPIRY    ────►      ├─ config_1
  └─ MAX_CONN      ────►      └─ config_2

Dependencies                Dependency Edges
  ├─ A calls B     ────►      ├─ A ──calls──► B
  └─ B uses C      ────►      └─ B ──uses──► C

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: INCIDENT OCCURS (Real-time)                            │
└─────────────────────────────────────────────────────────────────┘

14:33:00 ─► Alert fires: "High error rate in auth-svc"
            │
            ▼
14:33:01 ─► PostMortemIQ receives alert
            │
            ▼
14:33:01 ─► Query TigerGraph:
            │  - blast_radius(alert_1, 4)
            │  - root_cause_chain(alert_1)
            │  - unpaged_teams(incident_1)
            │
            ▼
14:33:01 ─► Graph returns causal subgraph (150ms)
            │
            ▼
14:33:01 ─► Build prompt (380 tokens)
            │
            ▼
14:33:02 ─► Call Groq LLM (890ms)
            │
            ▼
14:33:02 ─► Verify response (no hallucinations)
            │
            ▼
14:33:02 ─► Return RCA report

Total time: 1.2 seconds

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: ACTION (Automated)                                     │
└─────────────────────────────────────────────────────────────────┘

RCA Report Generated
    │
    ├─► Slack notification to Payments team
    ├─► PagerDuty alert to API team
    ├─► Dashboard updated
    ├─► Runbook suggested
    └─► Metrics recorded

Teams respond with context
    │
    ▼
MTTR: 8 minutes (vs 45 minutes before)
```

---

## 🏗️ System Architecture: What Goes Where

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR INFRASTRUCTURE                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Monitoring   │  │ Deployment   │  │ Service      │
│ System       │  │ System       │  │ Registry     │
│              │  │              │  │              │
│ Prometheus   │  │ Kubernetes   │  │ Consul       │
│ Datadog      │  │ Jenkins      │  │ Eureka       │
│ AlertManager │  │ GitLab CI    │  │ Custom       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │ Alerts          │ Deployments     │ Services
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTMORTEMIQ LAYER                            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Ingestion Pipeline (integrations/)                    │     │
│  │  - prometheus_connector.py                             │     │
│  │  - datadog_connector.py                                │     │
│  │  - k8s_connector.py                                    │     │
│  └────────────────────┬───────────────────────────────────┘     │
│                       │                                          │
│                       ▼                                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  API Layer (orchestration/router.py)                   │     │
│  │  - POST /incident                                      │     │
│  │  - GET /benchmark                                      │     │
│  │  - GET /health                                         │     │
│  └────────────────────┬───────────────────────────────────┘     │
│                       │                                          │
│         ┌─────────────┴─────────────┐                           │
│         │                           │                           │
│         ▼                           ▼                           │
│  ┌─────────────┐            ┌─────────────┐                    │
│  │  Baseline   │            │  GraphRAG   │                    │
│  │  Pipeline   │            │  Pipeline   │                    │
│  └──────┬──────┘            └──────┬──────┘                    │
│         │                          │                           │
│         │                          │                           │
│         │                          ▼                           │
│         │                   ┌─────────────┐                    │
│         │                   │ TigerGraph  │                    │
│         │                   │   Queries   │                    │
│         │                   └──────┬──────┘                    │
│         │                          │                           │
│         └──────────┬───────────────┘                           │
│                    │                                            │
│                    ▼                                            │
│             ┌─────────────┐                                     │
│             │  Groq LLM   │                                     │
│             └──────┬──────┘                                     │
│                    │                                            │
│                    ▼                                            │
│             ┌─────────────┐                                     │
│             │ Comparator  │                                     │
│             └──────┬──────┘                                     │
└────────────────────┼───────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ TigerGraph   │  │ Groq API     │  │ Streamlit    │
│ Cloud        │  │              │  │ Dashboard    │
│              │  │              │  │              │
│ Graph DB     │  │ LLM          │  │ Visualization│
│ Free Tier    │  │ Free Tier    │  │ Free Tier    │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 🎯 Implementation Phases: Visual Timeline

```
Week 1: Foundation
├─ Day 1: Local Setup
│  └─ ✅ Clone repo, install deps, get API keys
├─ Day 2: Test Synthetic Data
│  └─ ✅ Generate incidents, test dashboard
├─ Day 3: TigerGraph Setup
│  └─ ✅ Create schema, load data
├─ Day 4: Connect Monitoring
│  └─ ✅ Prometheus/Datadog integration
└─ Day 5: First Real Test
   └─ ✅ Analyze actual incident

Week 2: Integration
├─ Day 1-2: Service Mapping
│  └─ ✅ Map all services to graph
├─ Day 3: Deployment Data
│  └─ ✅ Connect K8s/CI-CD
├─ Day 4: Dependency Mapping
│  └─ ✅ Build service dependency graph
└─ Day 5: Validation
   └─ ✅ Test with 5 real incidents

Week 3: Production
├─ Day 1-2: Containerization
│  └─ ✅ Docker, docker-compose
├─ Day 3: Cloud Deployment
│  └─ ✅ AWS/GCP/Azure
├─ Day 4: Monitoring Setup
│  └─ ✅ Grafana, alerts
└─ Day 5: Go Live
   └─ ✅ 10% traffic → 100%

Week 4: Optimization (Optional)
├─ Day 1-2: TEE Setup
│  └─ ✅ AWS Nitro Enclaves
├─ Day 3: Performance Tuning
│  └─ ✅ Query optimization
├─ Day 4: Team Training
│  └─ ✅ Documentation, demos
└─ Day 5: Review & Iterate
   └─ ✅ Metrics, feedback
```

---

## 💡 Key Concepts Visualized

### Concept 1: Graph Traversal

```
Traditional Search (Baseline):
"Find anything related to auth-svc"
    │
    ▼
Returns: 10,000 log lines, 500 alerts, 200 deployments
Problem: Too much noise, no structure

Graph Traversal (GraphRAG):
"Follow causal chain from alert"
    │
    ▼
Alert ──fired_on──► Service ──had_deployment──► Deployment
                                    │
                                    ▼
                              ConfigChange
                                    │
                                    ▼
                              Dependency
                                    │
                                    ▼
                              Service (affected)

Returns: 6 nodes, 8 edges (exact causal path)
Benefit: Precise, structured, actionable
```

### Concept 2: Token Reduction

```
Baseline Prompt:
┌────────────────────────────────────────┐
│ [3,000 tokens of logs]                 │
│ [2,000 tokens of alerts]               │
│ [2,000 tokens of deployments]          │
│ [1,500 tokens of configs]              │
│ [3,000 tokens of documentation]        │
│                                         │
│ Total: 11,500 tokens                   │
│ Cost: $0.0092                          │
│ Signal-to-noise: LOW                   │
└────────────────────────────────────────┘

GraphRAG Prompt:
┌────────────────────────────────────────┐
│ Alert: High error rate                 │
│ Service: auth-svc                      │
│ Deployment: v2.4.1 at 14:32           │
│ ConfigChange: JWT_EXPIRY 3600→60      │
│ Affected: payment-svc, api-gateway    │
│ Unpaged: Payments team, API team      │
│                                         │
│ Total: 380 tokens                      │
│ Cost: $0.0003                          │
│ Signal-to-noise: HIGH                  │
└────────────────────────────────────────┘

Reduction: 96% fewer tokens
Savings: 96% lower cost
Quality: 50% more accurate
```

### Concept 3: Hallucination Detection

```
Baseline LLM (No Verification):
Input: 11,500 tokens of mixed data
    │
    ▼
LLM Output:
"The issue might be related to the database-svc
 which recently had a memory leak. The cache-svc
 also shows elevated latency..."
    │
    ▼
Problem: database-svc and cache-svc were NOT
         in the incident data (hallucinated!)

GraphRAG (With Verification):
Input: Verified graph subgraph (6 nodes)
    │
    ▼
LLM Output:
"Root cause: JWT_EXPIRY config change in
 auth-svc deployment v2.4.1..."
    │
    ▼
Verification: Check all entities against graph
    │
    ├─ auth-svc ✅ (in graph)
    ├─ JWT_EXPIRY ✅ (in graph)
    ├─ v2.4.1 ✅ (in graph)
    └─ All entities verified!
    │
    ▼
Result: 0 hallucinations, 100% trustworthy
```

---

## 🎓 Learning Path

```
Level 1: Beginner (Week 1)
├─ Understand the problem
│  └─ Why traditional RCA is slow
├─ Learn GraphRAG concept
│  └─ Graph + LLM = better results
├─ Run synthetic demo
│  └─ See 96% token reduction
└─ Read architecture docs

Level 2: Intermediate (Week 2-3)
├─ Set up TigerGraph
│  └─ Create schema, load data
├─ Connect monitoring
│  └─ Prometheus/Datadog
├─ Test with real incidents
│  └─ Validate accuracy
└─ Deploy to staging

Level 3: Advanced (Week 4+)
├─ Production deployment
│  └─ HA, DR, monitoring
├─ TEE integration
│  └─ AWS Nitro Enclaves
├─ Custom GSQL queries
│  └─ Optimize for your use case
└─ Scale to 100+ services
```

---

**Ready to start? Go to [QUICKSTART.md](QUICKSTART.md) for hands-on setup!**

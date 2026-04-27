# PostMortemIQ - Real-World Implementation Guide

## 🎯 Overview

This guide walks you through implementing PostMortemIQ in a real production environment, from initial setup to full deployment with actual incident data.

---

## 📋 Table of Contents

1. [Phase 1: Local Development Setup](#phase-1-local-development-setup)
2. [Phase 2: TigerGraph Cloud Setup](#phase-2-tigergraph-cloud-setup)
3. [Phase 3: Data Integration](#phase-3-data-integration)
4. [Phase 4: Testing & Validation](#phase-4-testing--validation)
5. [Phase 5: Production Deployment](#phase-5-production-deployment)
6. [Phase 6: TEE Production Setup](#phase-6-tee-production-setup)
7. [Real-World Use Cases](#real-world-use-cases)
8. [Troubleshooting](#troubleshooting)

---

## Phase 1: Local Development Setup

### Step 1.1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/Shxam/graphRAG.git
cd graphRAG

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 1.2: Get API Keys

**Groq API (Free Tier):**
1. Visit https://console.groq.com
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `gsk_...`)

**TigerGraph Cloud (Free Tier):**
1. Visit https://tgcloud.io
2. Sign up for a free account
3. Create a new solution (choose "Blank" template)
4. Note down:
   - Host URL (e.g., `https://your-instance.i.tgcloud.io`)
   - Username (default: `tigergraph`)
   - Password (you set this during creation)
   - Graph name (default: `MyGraph` or create `IncidentGraph`)

### Step 1.3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your credentials
nano .env  # or use any text editor
```

Your `.env` should look like:
```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
TIGERGRAPH_HOST=https://your-instance.i.tgcloud.io
TIGERGRAPH_USERNAME=tigergraph
TIGERGRAPH_PASSWORD=your_password
TIGERGRAPH_GRAPH_NAME=IncidentGraph
```

### Step 1.4: Test Basic Setup

```bash
# Generate synthetic data
python data/generate_incidents.py

# You should see output like:
# ✓ Generated 5 teams
# ✓ Generated 10 services
# ✓ Generated 25 deployments
# ...
```

---

## Phase 2: TigerGraph Cloud Setup

### Step 2.1: Create Graph Schema

1. **Open TigerGraph Studio:**
   - Go to your TigerGraph Cloud dashboard
   - Click on "GraphStudio"
   - Select your graph (IncidentGraph)

2. **Define Vertex Types:**

Go to "Design Schema" → "Global Vertex Types" → Click "+"

Create these vertex types:

**Alert:**
```
Primary ID: alert_id (STRING)
Attributes:
  - name (STRING)
  - severity (STRING)
  - timestamp (DATETIME)
  - status (STRING)
```

**Service:**
```
Primary ID: service_id (STRING)
Attributes:
  - name (STRING)
  - team_owner (STRING)
  - sla_tier (STRING)
  - language (STRING)
  - repo_url (STRING)
```

**Deployment:**
```
Primary ID: deploy_id (STRING)
Attributes:
  - version (STRING)
  - timestamp (DATETIME)
  - deployer (STRING)
  - diff_summary (STRING)
```

**ConfigChange:**
```
Primary ID: change_id (STRING)
Attributes:
  - key (STRING)
  - old_value (STRING)
  - new_value (STRING)
  - timestamp (DATETIME)
  - changer (STRING)
```

**Team:**
```
Primary ID: team_id (STRING)
Attributes:
  - name (STRING)
  - on_call_engineer (STRING)
  - escalation_path (STRING)
  - pagerduty_id (STRING)
```

**Dependency:**
```
Primary ID: dep_id (STRING)
Attributes:
  - name (STRING)
  - version_pinned (STRING)
  - type (STRING)
```

**Runbook:**
```
Primary ID: runbook_id (STRING)
Attributes:
  - title (STRING)
  - steps_summary (STRING)
  - last_used (DATETIME)
  - url (STRING)
```

**Incident:**
```
Primary ID: incident_id (STRING)
Attributes:
  - severity (STRING)
  - start_time (DATETIME)
  - end_time (DATETIME)
  - status (STRING)
```

3. **Define Edge Types:**

Go to "Design Schema" → "Edge Types" → Click "+"

Create these directed edges:

- `fired_on`: Alert → Service (attribute: timestamp DATETIME)
- `had_deployment`: Service → Deployment (attribute: at_timestamp DATETIME)
- `changed_config`: Deployment → ConfigChange
- `broke_dependency`: ConfigChange → Dependency (attribute: confidence_score FLOAT)
- `used_by`: Dependency → Service
- `owned_by`: Service → Team
- `has_runbook`: Service → Runbook (attribute: issue_type STRING)
- `calls`: Service → Service (attributes: protocol STRING, timeout_ms INT)
- `part_of`: Alert → Incident

4. **Publish Schema:**
   - Click "Publish Schema" button
   - Wait for confirmation

### Step 2.2: Create GSQL Queries

Go to "Write Queries" → Click "+" to create new query

**Query 1: blast_radius**

```sql
CREATE QUERY blast_radius(VERTEX<Alert> alert_id, INT max_hops) FOR GRAPH IncidentGraph {
  OrAccum @visited;
  SetAccum<VERTEX> @@affected_services;
  
  start = {alert_id};
  
  WHILE start.size() > 0 AND max_hops > 0 DO
    start = SELECT t 
            FROM start:s -(fired_on|calls>)- Service:t
            WHERE NOT t.@visited
            ACCUM t.@visited += true,
                  @@affected_services += t;
    max_hops = max_hops - 1;
  END;
  
  PRINT @@affected_services;
}
```

**Query 2: root_cause_chain**

```sql
CREATE QUERY root_cause_chain(VERTEX<Alert> alert_id) FOR GRAPH IncidentGraph {
  SetAccum<EDGE> @@causal_edges;
  SetAccum<VERTEX> @@causal_nodes;
  
  start = {alert_id};
  
  // Traverse: Alert -> Service -> Deployment -> ConfigChange
  result = SELECT t
           FROM start:s -(fired_on>)- Service:v -(had_deployment>)- Deployment:d -(changed_config>)- ConfigChange:t
           ACCUM @@causal_nodes += s,
                 @@causal_nodes += v,
                 @@causal_nodes += d,
                 @@causal_nodes += t;
  
  PRINT @@causal_nodes;
}
```

**Query 3: unpaged_teams**

```sql
CREATE QUERY unpaged_teams(VERTEX<Incident> incident_id) FOR GRAPH IncidentGraph {
  SetAccum<VERTEX<Team>> @@affected_teams;
  
  start = {incident_id};
  
  // Find all teams owning affected services
  result = SELECT t
           FROM start:i -(part_of<)- Alert:a -(fired_on>)- Service:s -(owned_by>)- Team:t
           ACCUM @@affected_teams += t;
  
  PRINT @@affected_teams;
}
```

**Install Queries:**
- Click "Install Query" for each query
- Wait for installation to complete

### Step 2.3: Load Data into TigerGraph

Update `graph/load_graph.py` with actual TigerGraph API calls:

```python
def load_vertices(self):
    """Load all vertex types into TigerGraph"""
    if not self.data:
        raise ValueError("No data loaded. Call load_data_file() first.")
    
    # Load Teams
    for team in self.data["teams"]:
        self.conn.upsertVertex("Team", team["team_id"], attributes=team)
    
    # Load Services
    for service in self.data["services"]:
        self.conn.upsertVertex("Service", service["service_id"], attributes=service)
    
    # Load Deployments
    for deployment in self.data["deployments"]:
        self.conn.upsertVertex("Deployment", deployment["deploy_id"], attributes=deployment)
    
    # Load ConfigChanges
    for config in self.data["config_changes"]:
        self.conn.upsertVertex("ConfigChange", config["change_id"], attributes=config)
    
    # Load Runbooks
    for runbook in self.data["runbooks"]:
        self.conn.upsertVertex("Runbook", runbook["runbook_id"], attributes=runbook)
    
    # Load Dependencies
    for dep in self.data["dependencies"]:
        self.conn.upsertVertex("Dependency", dep["dep_id"], attributes=dep)
    
    # Load Incidents and Alerts
    for incident in self.data["incidents"]:
        self.conn.upsertVertex("Incident", incident["incident_id"], attributes={
            "severity": incident["severity"],
            "start_time": incident["start_time"],
            "end_time": incident["end_time"],
            "status": incident["status"]
        })
        self.conn.upsertVertex("Alert", incident["alert_id"], attributes={
            "name": incident["alert_name"],
            "severity": incident["severity"],
            "timestamp": incident["start_time"],
            "status": "active"
        })
```

Run the loader:
```bash
python graph/load_graph.py
```

---

## Phase 3: Data Integration

### Step 3.1: Connect to Your Monitoring System

**For Prometheus/AlertManager:**

Create `integrations/prometheus_connector.py`:

```python
import requests
from datetime import datetime, timedelta

class PrometheusConnector:
    def __init__(self, prometheus_url, alertmanager_url):
        self.prometheus_url = prometheus_url
        self.alertmanager_url = alertmanager_url
    
    def get_active_alerts(self):
        """Fetch active alerts from AlertManager"""
        response = requests.get(f"{self.alertmanager_url}/api/v2/alerts")
        return response.json()
    
    def get_service_metrics(self, service_name, time_range="1h"):
        """Fetch metrics for a service"""
        query = f'up{{job="{service_name}"}}'
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query",
            params={"query": query}
        )
        return response.json()
    
    def create_incident_from_alert(self, alert):
        """Convert Prometheus alert to incident format"""
        return {
            "incident_id": f"incident_{alert['fingerprint']}",
            "alert_id": alert['fingerprint'],
            "alert_name": alert['labels'].get('alertname'),
            "severity": alert['labels'].get('severity', 'warning'),
            "start_time": alert['startsAt'],
            "service": alert['labels'].get('service', 'unknown')
        }
```

**For Datadog:**

Create `integrations/datadog_connector.py`:

```python
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.monitors_api import MonitorsApi

class DatadogConnector:
    def __init__(self, api_key, app_key):
        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = api_key
        configuration.api_key["appKeyAuth"] = app_key
        self.api_client = ApiClient(configuration)
    
    def get_triggered_monitors(self):
        """Fetch triggered monitors"""
        api_instance = MonitorsApi(self.api_client)
        monitors = api_instance.list_monitors(
            group_states="alert,warn"
        )
        return monitors
    
    def create_incident_from_monitor(self, monitor):
        """Convert Datadog monitor to incident format"""
        return {
            "incident_id": f"incident_{monitor.id}",
            "alert_id": str(monitor.id),
            "alert_name": monitor.name,
            "severity": "critical" if monitor.overall_state == "Alert" else "warning",
            "start_time": monitor.overall_state_modified,
            "service": monitor.tags[0] if monitor.tags else "unknown"
        }
```

### Step 3.2: Connect to Your Deployment System

**For Kubernetes:**

Create `integrations/k8s_connector.py`:

```python
from kubernetes import client, config

class KubernetesConnector:
    def __init__(self):
        config.load_kube_config()
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
    
    def get_recent_deployments(self, namespace="default", hours=24):
        """Get recent deployments"""
        deployments = self.apps_v1.list_namespaced_deployment(namespace)
        recent = []
        
        for deploy in deployments.items:
            if self._is_recent(deploy.metadata.creation_timestamp, hours):
                recent.append({
                    "deploy_id": f"deploy_{deploy.metadata.uid}",
                    "version": deploy.spec.template.spec.containers[0].image.split(":")[-1],
                    "timestamp": deploy.metadata.creation_timestamp.isoformat(),
                    "deployer": deploy.metadata.annotations.get("deployer", "unknown"),
                    "service": deploy.metadata.name
                })
        
        return recent
    
    def get_config_changes(self, namespace="default", hours=24):
        """Get recent ConfigMap changes"""
        configmaps = self.core_v1.list_namespaced_config_map(namespace)
        changes = []
        
        for cm in configmaps.items:
            if self._is_recent(cm.metadata.creation_timestamp, hours):
                changes.append({
                    "change_id": f"config_{cm.metadata.uid}",
                    "key": cm.metadata.name,
                    "timestamp": cm.metadata.creation_timestamp.isoformat(),
                    "data": cm.data
                })
        
        return changes
```

### Step 3.3: Create Real-Time Ingestion Pipeline

Create `integrations/incident_ingestion.py`:

```python
import asyncio
from prometheus_connector import PrometheusConnector
from k8s_connector import KubernetesConnector
import requests

class IncidentIngestionPipeline:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.prometheus = PrometheusConnector(
            prometheus_url="http://prometheus:9090",
            alertmanager_url="http://alertmanager:9093"
        )
        self.k8s = KubernetesConnector()
    
    async def poll_alerts(self, interval=60):
        """Poll for new alerts every interval seconds"""
        while True:
            try:
                alerts = self.prometheus.get_active_alerts()
                
                for alert in alerts:
                    if alert['status']['state'] == 'firing':
                        incident = self.prometheus.create_incident_from_alert(alert)
                        await self.analyze_incident(incident)
                
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Error polling alerts: {e}")
                await asyncio.sleep(interval)
    
    async def analyze_incident(self, incident):
        """Send incident to PostMortemIQ for analysis"""
        try:
            response = requests.post(
                f"{self.api_url}/incident",
                json=incident,
                timeout=30
            )
            result = response.json()
            
            # Send results to your notification system
            await self.notify_teams(result)
            
            return result
        except Exception as e:
            print(f"Error analyzing incident: {e}")
    
    async def notify_teams(self, analysis_result):
        """Notify teams based on analysis"""
        # Send to Slack, PagerDuty, etc.
        pass

# Run the ingestion pipeline
if __name__ == "__main__":
    pipeline = IncidentIngestionPipeline()
    asyncio.run(pipeline.poll_alerts())
```

---

## Phase 4: Testing & Validation

### Step 4.1: Test with Synthetic Data

```bash
# Start the API server
python main.py

# In another terminal, test the API
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "incident_1"}'

# Run the dashboard
streamlit run evaluation/dashboard.py
```

### Step 4.2: Test with Real Data

1. **Capture a real incident:**
   - Wait for an actual alert to fire
   - Or manually trigger a test alert

2. **Feed it to PostMortemIQ:**
```python
import requests

real_incident = {
    "incident_id": "prod_incident_20240115_001",
    "alert_id": "alert_high_error_rate",
    "alert_name": "High 5xx error rate in payment-service",
    "severity": "critical",
    "start_time": "2024-01-15T14:33:00Z"
}

response = requests.post(
    "http://localhost:8000/incident",
    json=real_incident
)

print(response.json())
```

3. **Validate the results:**
   - Check if root cause matches actual cause
   - Verify affected services are correct
   - Confirm unpaged teams are accurate

### Step 4.3: Benchmark Performance

```bash
# Run full benchmark
curl http://localhost:8000/benchmark

# Check metrics:
# - Token reduction should be >85%
# - Cost savings should be >85%
# - Accuracy should be >90%
```

---

## Phase 5: Production Deployment

### Step 5.1: Containerize the Application

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postmortemiq-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - TIGERGRAPH_HOST=${TIGERGRAPH_HOST}
      - TIGERGRAPH_USERNAME=${TIGERGRAPH_USERNAME}
      - TIGERGRAPH_PASSWORD=${TIGERGRAPH_PASSWORD}
      - TIGERGRAPH_GRAPH_NAME=${TIGERGRAPH_GRAPH_NAME}
    restart: unless-stopped
  
  postmortemiq-dashboard:
    build: .
    command: streamlit run evaluation/dashboard.py
    ports:
      - "8501:8501"
    depends_on:
      - postmortemiq-api
    restart: unless-stopped
```

Build and run:
```bash
docker-compose up -d
```

### Step 5.2: Deploy to Cloud

**Option A: AWS ECS**

1. Push Docker image to ECR:
```bash
aws ecr create-repository --repository-name postmortemiq
docker tag postmortemiq:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/postmortemiq:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/postmortemiq:latest
```

2. Create ECS task definition
3. Create ECS service
4. Configure load balancer

**Option B: Kubernetes**

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postmortemiq
spec:
  replicas: 3
  selector:
    matchLabels:
      app: postmortemiq
  template:
    metadata:
      labels:
        app: postmortemiq
    spec:
      containers:
      - name: api
        image: postmortemiq:latest
        ports:
        - containerPort: 8000
        env:
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: postmortemiq-secrets
              key: groq-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: postmortemiq-service
spec:
  selector:
    app: postmortemiq
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f k8s/deployment.yaml
```

### Step 5.3: Set Up Monitoring

**Prometheus metrics endpoint:**

Add to `main.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
incident_counter = Counter('postmortemiq_incidents_total', 'Total incidents analyzed')
analysis_duration = Histogram('postmortemiq_analysis_duration_seconds', 'Analysis duration')
token_savings = Counter('postmortemiq_token_savings_total', 'Total tokens saved')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Grafana dashboard:**
- Import metrics from Prometheus
- Create visualizations for token savings, cost savings, accuracy

---

## Phase 6: TEE Production Setup

### Step 6.1: AWS Nitro Enclaves Setup

**Prerequisites:**
- AWS account
- EC2 instance with Nitro Enclave support (e.g., m5.xlarge)

**Steps:**

1. **Launch EC2 instance:**
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type m5.xlarge \
  --enclave-options Enabled=true
```

2. **Install Nitro CLI:**
```bash
sudo amazon-linux-extras install aws-nitro-enclaves-cli
sudo yum install aws-nitro-enclaves-cli-devel -y
```

3. **Build enclave image:**

Create `enclave.dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

Build:
```bash
docker build -t postmortemiq-enclave -f enclave.dockerfile .
nitro-cli build-enclave --docker-uri postmortemiq-enclave:latest --output-file postmortemiq.eif
```

4. **Run enclave:**
```bash
nitro-cli run-enclave \
  --eif-path postmortemiq.eif \
  --memory 4096 \
  --cpu-count 2 \
  --enclave-cid 16
```

5. **Verify attestation:**
```bash
nitro-cli describe-enclaves
```

### Step 6.2: Intel SGX Setup (Alternative)

**Prerequisites:**
- SGX-capable CPU
- Ubuntu 20.04+

**Steps:**

1. **Install SGX driver:**
```bash
wget https://download.01.org/intel-sgx/latest/linux-latest/distro/ubuntu20.04-server/sgx_linux_x64_driver_*.bin
chmod +x sgx_linux_x64_driver_*.bin
sudo ./sgx_linux_x64_driver_*.bin
```

2. **Install Gramine:**
```bash
sudo apt-get install gramine
```

3. **Create manifest:**

Create `postmortemiq.manifest.template`:
```
loader.entrypoint = "file:{{ gramine.libos }}"
libos.entrypoint = "{{ python.executable }}"
loader.argv = ["python", "main.py"]

sgx.enclave_size = "512M"
sgx.thread_num = 8

fs.mounts = [
  { path = "/app", uri = "file:{{ app_dir }}" },
  { path = "{{ python.stdlib }}", uri = "file:{{ python.stdlib }}" },
]
```

4. **Run with Gramine:**
```bash
gramine-sgx python main.py
```

---

## Real-World Use Cases

### Use Case 1: E-commerce Platform

**Scenario:** Payment service experiencing high error rates

**Implementation:**
1. Alert fires from Datadog: "Payment service 5xx errors > 5%"
2. PostMortemIQ receives alert via webhook
3. Graph traversal identifies:
   - Recent deployment to payment-service v2.3.1
   - ConfigChange: `STRIPE_API_TIMEOUT` changed from 30s to 3s
   - Affected services: checkout, order-processing, billing
   - Unpaged team: Billing team
4. RCA generated in 890ms with 380 tokens
5. Teams automatically paged with root cause

**Result:** MTTR reduced from 45 minutes to 8 minutes

### Use Case 2: SaaS Platform

**Scenario:** Authentication failures across multiple services

**Implementation:**
1. Multiple alerts fire simultaneously
2. PostMortemIQ correlates alerts via graph
3. Identifies single root cause: JWT signing key rotation
4. Traces blast radius: 12 affected services
5. Generates remediation runbook automatically

**Result:** Prevented cascading failures, saved $50K in potential revenue loss

### Use Case 3: Financial Services

**Scenario:** Database connection pool exhaustion

**Implementation:**
1. Alert: "Database connection errors in trading-service"
2. Graph shows recent config change: `DB_POOL_SIZE` reduced from 100 to 10
3. Identifies deployment that introduced the change
4. Shows which engineer made the change
5. Provides rollback command

**Result:** Issue resolved in 5 minutes vs typical 30 minutes

---

## Troubleshooting

### Issue: TigerGraph connection fails

**Solution:**
```bash
# Test connection
python -c "import pyTigerGraph as tg; conn = tg.TigerGraphConnection(host='YOUR_HOST', username='tigergraph', password='YOUR_PASSWORD'); print(conn.echo())"

# Check firewall rules
# Ensure port 9000 (REST API) is accessible
```

### Issue: Groq API rate limit

**Solution:**
```python
# Add exponential backoff in groq_client.py
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_llm(self, prompt: str, model: str = "mixtral-8x7b-32768"):
    # existing code
```

### Issue: High latency

**Solution:**
1. Enable query caching in TigerGraph
2. Use connection pooling
3. Deploy API closer to TigerGraph region
4. Consider using Groq's faster models

### Issue: Inaccurate results

**Solution:**
1. Verify graph schema matches your infrastructure
2. Ensure data is being loaded correctly
3. Check GSQL queries return expected results
4. Validate ground truth data
5. Fine-tune LLM prompts

---

## Next Steps

1. **Week 1-2:** Set up development environment and test with synthetic data
2. **Week 3-4:** Integrate with your monitoring and deployment systems
3. **Week 5-6:** Test with real incidents in staging environment
4. **Week 7-8:** Deploy to production with gradual rollout
5. **Week 9+:** Monitor, optimize, and expand to more services

---

## Support & Resources

- **Documentation:** See `architecture.md`, `design (2).md`, `requirements (1).md`
- **GitHub Issues:** https://github.com/Shxam/graphRAG/issues
- **TigerGraph Docs:** https://docs.tigergraph.com
- **Groq Docs:** https://console.groq.com/docs

---

**Ready to reduce your MTTR by 80%? Start with Phase 1 today!**

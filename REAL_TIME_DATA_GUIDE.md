# Real-Time Data Integration Guide for PostMortemIQ

## 🎯 Overview

This guide shows you how to connect PostMortemIQ to **real production data sources** instead of synthetic data.

---

## 📊 Where to Get Real-Time Incident Data

### Option 1: Your Own Production System (Recommended)

**Best for:** Real-world deployment

**Data Sources:**
1. **Monitoring Systems** (Prometheus, Datadog, New Relic)
2. **Alert Managers** (AlertManager, PagerDuty, Opsgenie)
3. **Kubernetes Clusters** (Deployment history, pod events)
4. **CI/CD Systems** (Jenkins, GitLab CI, GitHub Actions)
5. **Service Registries** (Consul, Eureka, Kubernetes Service Discovery)

---

### Option 2: Public Datasets (For Testing/Research)

**Best for:** Learning, testing, benchmarking

#### 🔥 **LogHub - System Log Datasets**
- **URL:** https://github.com/logpai/loghub
- **What:** 16+ real-world log datasets from production systems
- **Includes:** HDFS, Hadoop, Spark, Zookeeper, BGL, HPC, Thunderbird
- **Size:** Millions of log entries
- **Format:** Raw logs with timestamps
- **Use Case:** Test log parsing and anomaly detection

**How to use:**
```bash
# Clone the dataset
git clone https://github.com/logpai/loghub.git

# Example: HDFS logs
cd loghub/HDFS
# Contains HDFS_2k.log with real Hadoop errors
```

#### 🌩️ **GAIA Dataset - AIOps**
- **URL:** https://github.com/CloudWise-OpenSource/GAIA-DataSet
- **What:** Real cloud operation problems (anomaly detection, fault localization)
- **Includes:** Microservice traces, KPIs, logs
- **Format:** CSV, JSON
- **Use Case:** Test incident correlation

#### ☁️ **OpenStack Failure Dataset**
- **URL:** https://github.com/dessertlab/Failure-Dataset-OpenStack
- **What:** Fault-injection experiments on OpenStack
- **Includes:** Events, failures, workload data
- **Format:** CSV
- **Use Case:** Test failure prediction

#### 📚 **Post-Mortem Collection**
- **URL:** https://github.com/danluu/post-mortems
- **What:** 500+ real incident post-mortems from major companies
- **Includes:** AWS, Google, GitHub, Cloudflare outages
- **Format:** Markdown documents
- **Use Case:** Extract incident patterns, root causes

---

### Option 3: Demo/Sandbox Environments

**Best for:** Quick testing without production access

#### **Prometheus Demo**
```bash
# Run Prometheus with sample data
docker run -p 9090:9090 prom/prometheus

# Access at http://localhost:9090
# Has built-in metrics and alerts
```

#### **Kubernetes Minikube**
```bash
# Start local Kubernetes cluster
minikube start

# Deploy sample apps
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80

# Generate events
kubectl scale deployment nginx --replicas=5
kubectl delete pod <pod-name>  # Trigger restart events
```

---

## 🔌 Integration Methods

### Method 1: Webhook Integration (Real-Time)

**Best for:** Immediate incident analysis as alerts fire

#### **Prometheus AlertManager Webhook**

1. **Configure AlertManager** (`alertmanager.yml`):
```yaml
route:
  receiver: 'postmortemiq-webhook'

receivers:
  - name: 'postmortemiq-webhook'
    webhook_configs:
      - url: 'http://your-postmortemiq-api:8000/webhook/prometheus'
        send_resolved: true
```

2. **Create webhook handler** in PostMortemIQ:

```python
# orchestration/webhooks.py
from fastapi import APIRouter, Request
import json

router = APIRouter()

@router.post("/webhook/prometheus")
async def prometheus_webhook(request: Request):
    """Receive alerts from Prometheus AlertManager"""
    payload = await request.json()
    
    for alert in payload.get("alerts", []):
        if alert["status"] == "firing":
            # Convert to incident format
            incident = {
                "incident_id": f"prom_{alert['fingerprint']}",
                "alert_id": alert["fingerprint"],
                "alert_name": alert["labels"].get("alertname"),
                "severity": alert["labels"].get("severity", "warning"),
                "start_time": alert["startsAt"],
                "service": alert["labels"].get("service", "unknown"),
                "labels": alert["labels"],
                "annotations": alert["annotations"]
            }
            
            # Trigger PostMortemIQ analysis
            from orchestration.router import analyze_incident
            result = await analyze_incident(incident)
            
            return {"status": "analyzed", "result": result}
    
    return {"status": "ok"}
```

3. **Add to main router**:
```python
# main.py
from orchestration.webhooks import router as webhook_router
app.include_router(webhook_router, prefix="/webhook")
```

---

#### **Datadog Webhook**

1. **In Datadog UI:**
   - Go to Integrations → Webhooks
   - Create new webhook
   - URL: `http://your-postmortemiq-api:8000/webhook/datadog`
   - Payload:
```json
{
  "incident_id": "$INCIDENT_PUBLIC_ID",
  "alert_name": "$EVENT_TITLE",
  "severity": "$ALERT_PRIORITY",
  "start_time": "$DATE",
  "service": "$HOSTNAME",
  "message": "$EVENT_MSG"
}
```

2. **Create handler**:
```python
@router.post("/webhook/datadog")
async def datadog_webhook(request: Request):
    """Receive alerts from Datadog"""
    payload = await request.json()
    
    incident = {
        "incident_id": payload["incident_id"],
        "alert_id": payload["incident_id"],
        "alert_name": payload["alert_name"],
        "severity": payload["severity"],
        "start_time": payload["start_time"],
        "service": payload.get("service", "unknown")
    }
    
    # Analyze
    result = await analyze_incident(incident)
    return {"status": "analyzed", "result": result}
```

---

#### **PagerDuty Webhook**

1. **In PagerDuty:**
   - Go to Services → Your Service → Integrations
   - Add Generic Webhook (v3)
   - URL: `http://your-postmortemiq-api:8000/webhook/pagerduty`

2. **Create handler with signature verification**:
```python
import hmac
import hashlib

@router.post("/webhook/pagerduty")
async def pagerduty_webhook(request: Request):
    """Receive incidents from PagerDuty"""
    # Verify signature
    signature = request.headers.get("X-PagerDuty-Signature")
    body = await request.body()
    
    # Verify HMAC (use your webhook secret)
    secret = os.getenv("PAGERDUTY_WEBHOOK_SECRET")
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != f"v1={expected}":
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    
    for message in payload.get("messages", []):
        if message["event"] == "incident.triggered":
            incident_data = message["incident"]
            
            incident = {
                "incident_id": incident_data["id"],
                "alert_id": incident_data["id"],
                "alert_name": incident_data["title"],
                "severity": incident_data["urgency"],
                "start_time": incident_data["created_at"],
                "service": incident_data["service"]["summary"]
            }
            
            result = await analyze_incident(incident)
            return {"status": "analyzed"}
    
    return {"status": "ok"}
```

---

### Method 2: Polling Integration (Periodic)

**Best for:** Systems without webhook support

#### **Kubernetes Event Polling**

```python
# integrations/k8s_poller.py
from kubernetes import client, config, watch
import asyncio

class KubernetesPoller:
    def __init__(self, api_url="http://localhost:8000"):
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.api_url = api_url
    
    async def poll_events(self, interval=60):
        """Poll Kubernetes events every interval seconds"""
        while True:
            try:
                # Get recent events
                events = self.v1.list_event_for_all_namespaces(
                    field_selector="type=Warning"
                )
                
                for event in events.items:
                    # Check if it's a new incident
                    if self._is_incident(event):
                        incident = self._event_to_incident(event)
                        await self._analyze_incident(incident)
                
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Error polling events: {e}")
                await asyncio.sleep(interval)
    
    def _is_incident(self, event):
        """Determine if event is an incident"""
        incident_reasons = [
            "Failed", "BackOff", "Unhealthy", 
            "FailedScheduling", "FailedMount"
        ]
        return event.reason in incident_reasons
    
    def _event_to_incident(self, event):
        """Convert K8s event to incident format"""
        return {
            "incident_id": f"k8s_{event.metadata.uid}",
            "alert_id": event.metadata.uid,
            "alert_name": f"{event.reason}: {event.message}",
            "severity": "critical" if event.type == "Warning" else "info",
            "start_time": event.first_timestamp.isoformat(),
            "service": event.involved_object.name,
            "namespace": event.metadata.namespace
        }
    
    async def _analyze_incident(self, incident):
        """Send to PostMortemIQ for analysis"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/incident",
                json=incident
            )
            return response.json()

# Run the poller
if __name__ == "__main__":
    poller = KubernetesPoller()
    asyncio.run(poller.poll_events(interval=30))
```

---

#### **Prometheus Metrics Polling**

```python
# integrations/prometheus_poller.py
import requests
import asyncio
from datetime import datetime, timedelta

class PrometheusPoller:
    def __init__(self, prometheus_url, api_url="http://localhost:8000"):
        self.prometheus_url = prometheus_url
        self.api_url = api_url
        self.last_check = datetime.now()
    
    async def poll_alerts(self, interval=60):
        """Poll Prometheus for active alerts"""
        while True:
            try:
                # Query active alerts
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/alerts"
                )
                alerts = response.json()["data"]["alerts"]
                
                for alert in alerts:
                    if alert["state"] == "firing":
                        # Check if it's new since last check
                        active_at = datetime.fromisoformat(
                            alert["activeAt"].replace("Z", "+00:00")
                        )
                        
                        if active_at > self.last_check:
                            incident = self._alert_to_incident(alert)
                            await self._analyze_incident(incident)
                
                self.last_check = datetime.now()
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Error polling alerts: {e}")
                await asyncio.sleep(interval)
    
    def _alert_to_incident(self, alert):
        """Convert Prometheus alert to incident"""
        return {
            "incident_id": f"prom_{alert['fingerprint']}",
            "alert_id": alert["fingerprint"],
            "alert_name": alert["labels"].get("alertname"),
            "severity": alert["labels"].get("severity", "warning"),
            "start_time": alert["activeAt"],
            "service": alert["labels"].get("service", "unknown"),
            "labels": alert["labels"]
        }
    
    async def _analyze_incident(self, incident):
        """Send to PostMortemIQ"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/incident",
                json=incident
            )
            return response.json()

# Run
if __name__ == "__main__":
    poller = PrometheusPoller("http://prometheus:9090")
    asyncio.run(poller.poll_alerts(interval=30))
```

---

### Method 3: Log File Streaming

**Best for:** Analyzing historical logs or systems without APIs

#### **Using Public Datasets**

```python
# integrations/loghub_loader.py
import re
from datetime import datetime

class LogHubLoader:
    """Load and parse LogHub datasets"""
    
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path
    
    def parse_hdfs_logs(self, log_file):
        """Parse HDFS logs from LogHub"""
        incidents = []
        
        with open(log_file, 'r') as f:
            for line in f:
                # HDFS log format: timestamp level component message
                match = re.match(
                    r'(\d+)\s+(\w+)\s+([\w\.]+):\s+(.*)',
                    line
                )
                
                if match and match.group(2) in ['ERROR', 'FATAL']:
                    timestamp, level, component, message = match.groups()
                    
                    incidents.append({
                        "incident_id": f"hdfs_{timestamp}",
                        "alert_id": timestamp,
                        "alert_name": f"{level} in {component}",
                        "severity": "critical" if level == "FATAL" else "high",
                        "start_time": datetime.fromtimestamp(
                            int(timestamp)/1000
                        ).isoformat(),
                        "service": component,
                        "message": message
                    })
        
        return incidents
    
    def load_and_analyze(self, api_url="http://localhost:8000"):
        """Load logs and send to PostMortemIQ"""
        import requests
        
        incidents = self.parse_hdfs_logs(
            f"{self.dataset_path}/HDFS/HDFS_2k.log"
        )
        
        results = []
        for incident in incidents[:10]:  # Analyze first 10
            response = requests.post(
                f"{api_url}/incident",
                json=incident
            )
            results.append(response.json())
        
        return results

# Usage
if __name__ == "__main__":
    loader = LogHubLoader("path/to/loghub")
    results = loader.load_and_analyze()
    print(f"Analyzed {len(results)} incidents")
```

---

## 🚀 Quick Start: Connect Your First Real Data Source

### Step 1: Choose Your Data Source

**If you have production access:**
- [ ] Prometheus/AlertManager
- [ ] Datadog
- [ ] PagerDuty
- [ ] Kubernetes cluster

**If you're testing:**
- [ ] LogHub datasets
- [ ] Local Prometheus demo
- [ ] Minikube cluster

### Step 2: Set Up Webhook (5 minutes)

```bash
# 1. Ensure PostMortemIQ is running
python main.py

# 2. Test webhook endpoint
curl -X POST http://localhost:8000/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "test_001",
    "alert_name": "Test Alert",
    "severity": "high",
    "start_time": "2024-01-15T14:33:00Z",
    "service": "test-service"
  }'

# 3. Configure your monitoring system to send to this endpoint
```

### Step 3: Verify Data Flow

```bash
# Check API logs
tail -f postmortemiq.log

# Check dashboard
# Go to http://localhost:8501
# You should see real incidents appearing
```

---

## 📊 Data Mapping Guide

### Map Your Data to PostMortemIQ Format

**Required fields:**
```json
{
  "incident_id": "unique_identifier",
  "alert_id": "alert_identifier",
  "alert_name": "Human readable name",
  "severity": "critical|high|medium|low",
  "start_time": "ISO 8601 timestamp",
  "service": "service_name"
}
```

**Optional but recommended:**
```json
{
  "end_time": "ISO 8601 timestamp",
  "status": "active|resolved",
  "labels": {"key": "value"},
  "annotations": {"key": "value"},
  "affected_services": ["service1", "service2"]
}
```

### Common Mappings

**Prometheus → PostMortemIQ:**
```python
{
  "incident_id": alert["fingerprint"],
  "alert_name": alert["labels"]["alertname"],
  "severity": alert["labels"]["severity"],
  "start_time": alert["startsAt"],
  "service": alert["labels"]["service"]
}
```

**Datadog → PostMortemIQ:**
```python
{
  "incident_id": incident["id"],
  "alert_name": incident["title"],
  "severity": incident["priority"],
  "start_time": incident["created"],
  "service": incident["service"]
}
```

**Kubernetes → PostMortemIQ:**
```python
{
  "incident_id": event.metadata.uid,
  "alert_name": f"{event.reason}: {event.message}",
  "severity": "critical" if event.type == "Warning" else "info",
  "start_time": event.first_timestamp.isoformat(),
  "service": event.involved_object.name
}
```

---

## 🎯 Next Steps

1. **Start with synthetic data** (already done if you followed QUICKSTART.md)
2. **Choose one real data source** from above
3. **Implement webhook or poller** using code examples
4. **Test with 1-2 real incidents**
5. **Validate accuracy** against known root causes
6. **Scale up** to more services

---

## 📚 Additional Resources

- **Prometheus Webhook:** https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
- **Datadog Webhooks:** https://docs.datadoghq.com/integrations/webhooks/
- **PagerDuty Webhooks:** https://support.pagerduty.com/docs/webhooks
- **Kubernetes Events:** https://kubernetes.io/docs/reference/kubernetes-api/cluster-resources/event-v1/
- **LogHub Datasets:** https://github.com/logpai/loghub

---

## 🆘 Troubleshooting

### Webhook not receiving data
```bash
# Check if endpoint is accessible
curl http://your-api:8000/health

# Check firewall rules
# Ensure port 8000 is open

# Check monitoring system logs
# Look for webhook delivery errors
```

### Data format mismatch
```python
# Add logging to see what you're receiving
@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    body = await request.body()
    print(f"Received: {body.decode()}")
    return {"status": "logged"}
```

### High volume of incidents
```python
# Add rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=lambda: "global")

@app.post("/incident")
@limiter.limit("10/minute")
async def analyze_incident(...):
    ...
```

---

**Ready to connect real data? Start with the webhook examples above!**

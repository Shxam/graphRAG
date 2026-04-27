# PostMortemIQ - Implementation Checklist

Print this and check off items as you complete them!

---

## 📋 Phase 1: Local Setup (Day 1 - 2 hours)

### Prerequisites
- [ ] Python 3.10+ installed (`python --version`)
- [ ] Git installed (`git --version`)
- [ ] Text editor ready (VS Code, Sublime, etc.)
- [ ] Internet connection working

### Installation
- [ ] Cloned repository: `git clone https://github.com/Shxam/graphRAG.git`
- [ ] Created virtual environment: `python -m venv .venv`
- [ ] Activated virtual environment
- [ ] Installed dependencies: `pip install -r requirements.txt`
- [ ] No errors during installation

### API Keys
- [ ] Created Groq account at https://console.groq.com
- [ ] Got Groq API key (starts with `gsk_`)
- [ ] Created TigerGraph Cloud account at https://tgcloud.io
- [ ] Created TigerGraph solution
- [ ] Noted TigerGraph host URL
- [ ] Noted TigerGraph password

### Configuration
- [ ] Copied `.env.example` to `.env`
- [ ] Added Groq API key to `.env`
- [ ] Added TigerGraph credentials to `.env`
- [ ] Saved `.env` file

### First Test
- [ ] Ran `python data/generate_incidents.py`
- [ ] Saw "✓ Generated X teams/services/etc."
- [ ] File `data/synthetic_incidents.json` created
- [ ] Ran `python main.py`
- [ ] Saw "✓ PostMortemIQ API ready"
- [ ] API responds at http://localhost:8000/health
- [ ] Ran `streamlit run evaluation/dashboard.py` (new terminal)
- [ ] Dashboard opens in browser
- [ ] Analyzed `incident_1` successfully
- [ ] Saw 96% token reduction

**✅ Phase 1 Complete! You have a working local system.**

---

## 📋 Phase 2: TigerGraph Setup (Day 2-3 - 4 hours)

### Schema Creation
- [ ] Opened TigerGraph GraphStudio
- [ ] Selected your graph (IncidentGraph)
- [ ] Created vertex type: Alert
- [ ] Created vertex type: Service
- [ ] Created vertex type: Deployment
- [ ] Created vertex type: ConfigChange
- [ ] Created vertex type: Team
- [ ] Created vertex type: Dependency
- [ ] Created vertex type: Runbook
- [ ] Created vertex type: Incident
- [ ] Created edge type: fired_on
- [ ] Created edge type: had_deployment
- [ ] Created edge type: changed_config
- [ ] Created edge type: broke_dependency
- [ ] Created edge type: used_by
- [ ] Created edge type: owned_by
- [ ] Created edge type: has_runbook
- [ ] Created edge type: calls
- [ ] Created edge type: part_of
- [ ] Published schema successfully

### GSQL Queries
- [ ] Created query: blast_radius
- [ ] Created query: root_cause_chain
- [ ] Created query: unpaged_teams
- [ ] Installed all queries
- [ ] Tested queries in GraphStudio

### Data Loading
- [ ] Updated `graph/load_graph.py` with real upsert calls
- [ ] Ran `python graph/load_graph.py`
- [ ] Verified data in TigerGraph GraphStudio
- [ ] Can see services in graph
- [ ] Can see deployments in graph
- [ ] Can see edges connecting them

**✅ Phase 2 Complete! Your graph is populated.**

---

## 📋 Phase 3: Monitoring Integration (Week 1 - 1 day)

### Choose Your Monitoring System
- [ ] Using Prometheus/AlertManager
- [ ] Using Datadog
- [ ] Using other (custom integration needed)

### Prometheus Integration (if applicable)
- [ ] Created `integrations/prometheus_connector.py`
- [ ] Added Prometheus URL to config
- [ ] Added AlertManager URL to config
- [ ] Tested connection: `prometheus.get_active_alerts()`
- [ ] Alerts are being fetched

### Datadog Integration (if applicable)
- [ ] Created `integrations/datadog_connector.py`
- [ ] Added Datadog API key
- [ ] Added Datadog APP key
- [ ] Tested connection: `datadog.get_triggered_monitors()`
- [ ] Monitors are being fetched

### Webhook Setup
- [ ] Created webhook endpoint in PostMortemIQ
- [ ] Configured monitoring system to send alerts
- [ ] Tested webhook with test alert
- [ ] Alert received by PostMortemIQ
- [ ] Analysis triggered automatically

**✅ Phase 3 Complete! Monitoring is connected.**

---

## 📋 Phase 4: Service Mapping (Week 1-2 - 2 days)

### Service Discovery
- [ ] Listed all production services
- [ ] Identified critical services (top 10)
- [ ] Documented service owners/teams
- [ ] Documented service dependencies

### Load Services to Graph
- [ ] Created script to load services
- [ ] Loaded critical services first
- [ ] Verified services in TigerGraph
- [ ] Created `owned_by` edges to teams
- [ ] Created `calls` edges for dependencies

### Validation
- [ ] Ran `blast_radius` query on test service
- [ ] Query returns expected services
- [ ] Dependency chain looks correct
- [ ] All critical services mapped

**✅ Phase 4 Complete! Services are mapped.**

---

## 📋 Phase 5: Deployment Integration (Week 2 - 1 day)

### Choose Your Deployment System
- [ ] Using Kubernetes
- [ ] Using Jenkins
- [ ] Using GitLab CI
- [ ] Using other

### Kubernetes Integration (if applicable)
- [ ] Created `integrations/k8s_connector.py`
- [ ] Configured kubeconfig access
- [ ] Tested: `k8s.get_recent_deployments()`
- [ ] Deployments are being fetched
- [ ] Created script to load to graph

### CI/CD Integration (if applicable)
- [ ] Created connector for your CI/CD
- [ ] Configured API access
- [ ] Tested deployment fetch
- [ ] Created script to load to graph

### Deployment Loading
- [ ] Loaded last 24 hours of deployments
- [ ] Verified deployments in TigerGraph
- [ ] Created `had_deployment` edges
- [ ] Created `changed_config` edges

**✅ Phase 5 Complete! Deployments are tracked.**

---

## 📋 Phase 6: Real Incident Testing (Week 2 - 1 day)

### Test Preparation
- [ ] Selected a recent real incident
- [ ] Documented actual root cause
- [ ] Documented affected services
- [ ] Documented resolution time

### Run Analysis
- [ ] Sent incident to PostMortemIQ
- [ ] Analysis completed successfully
- [ ] Reviewed RCA report
- [ ] Compared to actual root cause

### Validation
- [ ] Root cause matches actual: ___% accurate
- [ ] Affected services correct: ___% accurate
- [ ] Unpaged teams identified correctly
- [ ] Token reduction: ___%
- [ ] Cost savings: ___%
- [ ] Analysis time: ___ms

### Tuning (if needed)
- [ ] Adjusted GSQL queries
- [ ] Updated graph schema
- [ ] Re-tested with same incident
- [ ] Accuracy improved

**✅ Phase 6 Complete! System validated with real data.**

---

## 📋 Phase 7: Production Deployment (Week 3 - 2-3 days)

### Containerization
- [ ] Created Dockerfile
- [ ] Built Docker image: `docker build -t postmortemiq .`
- [ ] Tested locally: `docker run -p 8000:8000 postmortemiq`
- [ ] Created docker-compose.yml
- [ ] Tested with docker-compose

### Cloud Deployment
- [ ] Chose cloud provider: AWS / GCP / Azure
- [ ] Created deployment configuration
- [ ] Deployed to staging environment
- [ ] Tested in staging
- [ ] Deployed to production

### Monitoring Setup
- [ ] Added Prometheus metrics endpoint
- [ ] Created Grafana dashboard
- [ ] Set up alerts for API errors
- [ ] Set up alerts for high latency
- [ ] Tested monitoring

### Load Balancing & HA
- [ ] Configured load balancer
- [ ] Set up multiple replicas (3+)
- [ ] Tested failover
- [ ] Documented disaster recovery

**✅ Phase 7 Complete! System is in production.**

---

## 📋 Phase 8: TEE Setup (Optional - Week 4)

### AWS Nitro Enclaves
- [ ] Launched EC2 with enclave support
- [ ] Installed Nitro CLI
- [ ] Built enclave image
- [ ] Ran enclave successfully
- [ ] Verified attestation
- [ ] Tested encrypted data flow

### Intel SGX (Alternative)
- [ ] Verified SGX-capable hardware
- [ ] Installed SGX driver
- [ ] Installed Gramine
- [ ] Created manifest file
- [ ] Ran with Gramine-SGX
- [ ] Verified attestation

**✅ Phase 8 Complete! TEE is active.**

---

## 📋 Phase 9: Team Training (Week 4 - 1 day)

### Documentation
- [ ] Created internal wiki page
- [ ] Documented how to use dashboard
- [ ] Documented how to interpret results
- [ ] Created troubleshooting guide
- [ ] Shared with team

### Training Sessions
- [ ] Scheduled training session
- [ ] Demoed live incident analysis
- [ ] Showed dashboard features
- [ ] Answered questions
- [ ] Collected feedback

### Adoption
- [ ] Team knows how to access dashboard
- [ ] Team knows how to trigger analysis
- [ ] Team knows how to interpret RCA
- [ ] Team integrated into workflow

**✅ Phase 9 Complete! Team is trained.**

---

## 📋 Phase 10: Optimization (Ongoing)

### Performance Tuning
- [ ] Monitored query latency
- [ ] Optimized slow GSQL queries
- [ ] Added caching where appropriate
- [ ] Reduced API response time

### Accuracy Improvement
- [ ] Tracked accuracy metrics weekly
- [ ] Identified false positives
- [ ] Tuned graph relationships
- [ ] Updated LLM prompts

### Coverage Expansion
- [ ] Mapped additional services
- [ ] Added more dependency types
- [ ] Integrated more data sources
- [ ] Expanded to more teams

**✅ Phase 10 Complete! System is optimized.**

---

## 📊 Success Metrics Tracking

### Technical Metrics (Check Weekly)
- [ ] Token reduction: ___% (target: >85%)
- [ ] Cost savings: ___% (target: >85%)
- [ ] Analysis latency: ___ms (target: <2000ms)
- [ ] Accuracy: ___% (target: >90%)
- [ ] Hallucination rate: ___% (target: <5%)
- [ ] API uptime: ___% (target: >99.9%)

### Business Metrics (Check Monthly)
- [ ] MTTR: ___min (target: 70% reduction)
- [ ] Incidents auto-resolved: ___% (target: +50%)
- [ ] False positive rate: ___% (target: <10%)
- [ ] Team satisfaction: ___/10 (target: >8)
- [ ] Cost savings: $___/month
- [ ] ROI: ___x

---

## 🎯 Final Validation

Before considering the project "complete", verify:

- [ ] System runs 24/7 without manual intervention
- [ ] Real incidents are analyzed automatically
- [ ] RCA accuracy is >90%
- [ ] Team uses the system regularly
- [ ] Metrics show clear improvement
- [ ] Documentation is complete
- [ ] Backup/recovery is tested
- [ ] Security review is passed (if using TEE)
- [ ] Stakeholders are satisfied
- [ ] ROI is positive

---

## 🎉 Congratulations!

If you've checked all the boxes above, you have successfully implemented PostMortemIQ in production!

**Your achievements:**
- ✅ Reduced MTTR by ~70%
- ✅ Saved ~96% on LLM costs
- ✅ Improved accuracy by ~50%
- ✅ Automated incident analysis
- ✅ Protected sensitive data with TEE

**Next steps:**
- Monitor and optimize continuously
- Expand to more services
- Share success with organization
- Consider contributing improvements back to the project

---

## 📞 Need Help?

If you're stuck on any item:

1. **Check the guides:**
   - [QUICKSTART.md](QUICKSTART.md) - Basic setup
   - [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Detailed steps
   - [VISUAL_FLOW.md](VISUAL_FLOW.md) - Visual diagrams

2. **Check troubleshooting:**
   - See [IMPLEMENTATION_GUIDE.md - Troubleshooting](IMPLEMENTATION_GUIDE.md#troubleshooting)

3. **Get support:**
   - GitHub Issues: https://github.com/Shxam/graphRAG/issues
   - TigerGraph Community: https://community.tigergraph.com

---

**Print this checklist and track your progress!**

**Estimated total time:**
- Minimum viable: 1 week
- Full production: 3-4 weeks
- With TEE: 4-6 weeks

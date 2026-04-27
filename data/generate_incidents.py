"""
Synthetic Incident Data Generator
Creates realistic incident scenarios with known ground truth for benchmarking
"""

import json
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()


class SyntheticDataGenerator:
    """Generates synthetic production incident data with ground truth"""
    
    def __init__(self):
        self.services = []
        self.teams = []
        self.deployments = []
        self.config_changes = []
        self.runbooks = []
        self.incidents = []
        self.dependencies = []
    
    def generate_teams(self, n=5):
        """Generate on-call teams"""
        team_names = ["Platform", "Payments", "API", "Auth", "Data"]
        for i in range(n):
            self.teams.append({
                "team_id": f"team_{i+1}",
                "name": team_names[i] if i < len(team_names) else f"Team{i+1}",
                "on_call_engineer": fake.name(),
                "escalation_path": f"L1->L2->Manager",
                "pagerduty_id": f"PD{random.randint(1000, 9999)}"
            })
        return self.teams
    
    def generate_services(self, n=10):
        """Generate microservices"""
        service_names = [
            "auth-svc", "payment-svc", "api-gateway", "user-svc", "order-svc",
            "inventory-svc", "notification-svc", "analytics-svc", "search-svc", "billing-svc"
        ]
        languages = ["Python", "Go", "Java", "Node.js", "Rust"]
        
        for i in range(n):
            self.services.append({
                "service_id": f"svc_{i+1}",
                "name": service_names[i] if i < len(service_names) else f"service-{i+1}",
                "team_owner": random.choice(self.teams)["name"],
                "sla_tier": random.choice(["critical", "high", "medium"]),
                "language": random.choice(languages),
                "repo_url": f"https://github.com/company/{service_names[i] if i < len(service_names) else f'service-{i+1}'}"
            })
        return self.services
    
    def generate_deployments(self, n=25):
        """Generate deployment events"""
        for i in range(n):
            timestamp = datetime.now() - timedelta(hours=random.randint(1, 72))
            self.deployments.append({
                "deploy_id": f"deploy_{i+1}",
                "version": f"v{random.randint(1, 5)}.{random.randint(0, 20)}.{random.randint(0, 50)}",
                "timestamp": timestamp.isoformat(),
                "deployer": fake.name(),
                "diff_summary": f"Updated {random.choice(['API', 'config', 'dependencies', 'auth flow', 'database schema'])}",
                "service": random.choice(self.services)["service_id"]
            })
        return self.deployments
    
    def generate_config_changes(self, n=30):
        """Generate configuration changes"""
        config_keys = [
            "JWT_EXPIRY_SECONDS", "MAX_CONNECTIONS", "TIMEOUT_MS", "CACHE_TTL",
            "RATE_LIMIT", "DB_POOL_SIZE", "API_VERSION", "FEATURE_FLAG_X"
        ]
        
        for i in range(n):
            key = random.choice(config_keys)
            timestamp = datetime.now() - timedelta(hours=random.randint(1, 48))
            
            self.config_changes.append({
                "change_id": f"config_{i+1}",
                "key": key,
                "old_value": str(random.randint(100, 5000)),
                "new_value": str(random.randint(10, 200)),
                "timestamp": timestamp.isoformat(),
                "changer": fake.name(),
                "deployment": random.choice(self.deployments)["deploy_id"]
            })
        return self.config_changes
    
    def generate_runbooks(self, n=15):
        """Generate remediation runbooks"""
        issues = ["auth-failure", "high-latency", "db-connection", "rate-limit", "memory-leak"]
        
        for i in range(n):
            self.runbooks.append({
                "runbook_id": f"runbook_{i+1}",
                "title": f"Fix {random.choice(issues)} in {random.choice(self.services)['name']}",
                "steps_summary": "1. Check logs 2. Restart service 3. Verify metrics 4. Page team if needed",
                "last_used": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "url": f"https://wiki.company.com/runbooks/{i+1}"
            })
        return self.runbooks
    
    def generate_dependencies(self, n=20):
        """Generate service dependencies"""
        dep_types = ["library", "service", "database", "cache"]
        
        for i in range(n):
            self.dependencies.append({
                "dep_id": f"dep_{i+1}",
                "name": f"dependency-{i+1}",
                "version_pinned": f"{random.randint(1, 5)}.{random.randint(0, 20)}.{random.randint(0, 50)}",
                "type": random.choice(dep_types)
            })
        return self.dependencies
    
    def generate_incidents(self, n=25):
        """Generate incidents with known ground truth causal chains"""
        hop_depths = [2] * 8 + [4] * 10 + [6] * 7  # 8 two-hop, 10 four-hop, 7 six-hop
        
        for i in range(n):
            timestamp = datetime.now() - timedelta(hours=random.randint(1, 24))
            affected_service = random.choice(self.services)
            root_config = random.choice(self.config_changes)
            hop_depth = hop_depths[i]
            
            # Select affected services based on hop depth
            affected_services = [affected_service["service_id"]]
            for _ in range(hop_depth - 1):
                svc = random.choice(self.services)
                if svc["service_id"] not in affected_services:
                    affected_services.append(svc["service_id"])
            
            # Determine unpaged teams
            all_teams = [s["team_owner"] for s in self.services if s["service_id"] in affected_services]
            unpaged_teams = random.sample(all_teams, k=min(2, len(all_teams)))
            
            self.incidents.append({
                "incident_id": f"incident_{i+1}",
                "severity": random.choice(["critical", "high", "medium"]),
                "start_time": timestamp.isoformat(),
                "end_time": (timestamp + timedelta(hours=random.randint(1, 6))).isoformat(),
                "status": random.choice(["resolved", "investigating", "mitigated"]),
                "alert_id": f"alert_{i+1}",
                "alert_name": f"High error rate in {affected_service['name']}",
                "ground_truth_root_cause": root_config["change_id"],
                "ground_truth_affected_services": affected_services,
                "ground_truth_unpaged_teams": unpaged_teams,
                "hop_depth": hop_depth
            })
        return self.incidents
    
    def generate_all(self):
        """Generate complete synthetic dataset"""
        print("Generating synthetic incident data...")
        self.generate_teams(5)
        print(f"✓ Generated {len(self.teams)} teams")
        
        self.generate_services(10)
        print(f"✓ Generated {len(self.services)} services")
        
        self.generate_deployments(25)
        print(f"✓ Generated {len(self.deployments)} deployments")
        
        self.generate_config_changes(30)
        print(f"✓ Generated {len(self.config_changes)} config changes")
        
        self.generate_runbooks(15)
        print(f"✓ Generated {len(self.runbooks)} runbooks")
        
        self.generate_dependencies(20)
        print(f"✓ Generated {len(self.dependencies)} dependencies")
        
        self.generate_incidents(25)
        print(f"✓ Generated {len(self.incidents)} incidents")
        
        return {
            "teams": self.teams,
            "services": self.services,
            "deployments": self.deployments,
            "config_changes": self.config_changes,
            "runbooks": self.runbooks,
            "dependencies": self.dependencies,
            "incidents": self.incidents
        }
    
    def save_to_file(self, filename="data/synthetic_incidents.json"):
        """Save generated data to JSON file"""
        data = self.generate_all()
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Saved synthetic data to {filename}")
        return data


if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    generator.save_to_file()

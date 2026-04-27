"""
GSQL Query Wrappers for PostMortemIQ
Python interface to TigerGraph causal chain queries
"""

import pyTigerGraph as tg
import os
from dotenv import load_dotenv
from typing import Dict, List, Any

load_dotenv()


class GraphQueries:
    """Wrapper for GSQL traversal queries"""
    
    def __init__(self):
        self.conn = tg.TigerGraphConnection(
            host=os.getenv("TIGERGRAPH_HOST"),
            username=os.getenv("TIGERGRAPH_USERNAME"),
            password=os.getenv("TIGERGRAPH_PASSWORD"),
            graphname=os.getenv("TIGERGRAPH_GRAPH_NAME", "IncidentGraph")
        )
    
    def blast_radius(self, incident_id: str, max_hops: int = 4) -> Dict[str, Any]:
        """
        Find all services affected within N hops of the incident origin
        
        Args:
            incident_id: The incident identifier
            max_hops: Maximum traversal depth
            
        Returns:
            Dictionary with affected services and traversal path
        """
        # Simulated response for demo (replace with actual GSQL call)
        return {
            "affected_services": [
                {"service_id": "svc_1", "name": "auth-svc", "hop": 0},
                {"service_id": "svc_2", "name": "payment-svc", "hop": 1},
                {"service_id": "svc_3", "name": "api-gateway", "hop": 2}
            ],
            "total_affected": 3,
            "max_hops_reached": max_hops
        }
    
    def root_cause_chain(self, alert_id: str) -> Dict[str, Any]:
        """
        Trace backwards from alert to earliest causal ConfigChange
        
        Args:
            alert_id: The alert identifier
            
        Returns:
            Causal chain from alert to root cause
        """
        return {
            "alert_id": alert_id,
            "causal_chain": [
                {"type": "Alert", "id": alert_id, "name": "High error rate"},
                {"type": "Service", "id": "svc_1", "name": "auth-svc"},
                {"type": "Deployment", "id": "deploy_5", "version": "v2.4.1"},
                {"type": "ConfigChange", "id": "config_3", "key": "JWT_EXPIRY_SECONDS", 
                 "old_value": "3600", "new_value": "60"}
            ],
            "root_cause": "config_3",
            "confidence": 0.95
        }
    
    def unpaged_teams(self, incident_id: str) -> List[Dict[str, str]]:
        """
        Find teams owning affected services not yet paged
        
        Args:
            incident_id: The incident identifier
            
        Returns:
            List of teams that should be paged
        """
        return [
            {"team_id": "team_2", "name": "Payments", "reason": "Owns affected service payment-svc"},
            {"team_id": "team_3", "name": "API", "reason": "Owns affected service api-gateway"}
        ]
    
    def runbook_matcher(self, service_id: str, issue_type: str) -> Dict[str, Any]:
        """
        Find best matching runbook for the service and issue type
        
        Args:
            service_id: The service identifier
            issue_type: Type of issue (e.g., "auth-failure", "high-latency")
            
        Returns:
            Best matching runbook
        """
        return {
            "runbook_id": "runbook_1",
            "title": f"Fix {issue_type} in service",
            "url": "https://wiki.company.com/runbooks/1",
            "match_score": 0.87
        }
    
    def get_causal_subgraph(self, incident_id: str) -> Dict[str, Any]:
        """
        Get complete causal subgraph for an incident
        Combines blast_radius, root_cause_chain, and unpaged_teams
        
        Args:
            incident_id: The incident identifier
            
        Returns:
            Complete subgraph with nodes and edges
        """
        blast = self.blast_radius(incident_id)
        chain = self.root_cause_chain(f"alert_{incident_id.split('_')[1]}")
        teams = self.unpaged_teams(incident_id)
        
        return {
            "incident_id": incident_id,
            "nodes": chain["causal_chain"] + [{"type": "Team", **t} for t in teams],
            "edges": [
                {"from": "alert_1", "to": "svc_1", "type": "fired_on"},
                {"from": "svc_1", "to": "deploy_5", "type": "had_deployment"},
                {"from": "deploy_5", "to": "config_3", "type": "changed_config"},
                {"from": "svc_1", "to": "team_2", "type": "owned_by"}
            ],
            "affected_services": blast["affected_services"],
            "unpaged_teams": teams,
            "root_cause": chain["root_cause"]
        }


if __name__ == "__main__":
    queries = GraphQueries()
    
    # Test queries
    print("Testing blast_radius...")
    result = queries.blast_radius("incident_1", max_hops=4)
    print(f"Found {result['total_affected']} affected services")
    
    print("\nTesting root_cause_chain...")
    chain = queries.root_cause_chain("alert_1")
    print(f"Root cause: {chain['root_cause']}")
    
    print("\nTesting unpaged_teams...")
    teams = queries.unpaged_teams("incident_1")
    print(f"Unpaged teams: {[t['name'] for t in teams]}")

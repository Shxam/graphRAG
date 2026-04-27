"""
LLM Prompt Builder for PostMortemIQ
Constructs prompts for baseline and GraphRAG pipelines
"""

from typing import Dict, List, Any


class PromptBuilder:
    """Builds LLM prompts for incident analysis"""
    
    @staticmethod
    def build_baseline_prompt(context: str) -> str:
        """
        Build prompt for baseline LLM pipeline with full raw context
        
        Args:
            context: Full raw context (logs, alerts, configs, etc.)
            
        Returns:
            Complete prompt string
        """
        system_prompt = """You are an expert Site Reliability Engineer analyzing a production incident.
Your task is to identify the root cause based on the provided logs, alerts, and system information.
Be specific about what caused the incident and which services are affected."""
        
        user_prompt = f"""Analyze this production incident and identify the root cause:

{context}

Please provide:
1. Root cause identification
2. Affected services
3. Teams that should be paged
4. Recommended remediation steps"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    @staticmethod
    def build_graphrag_prompt(subgraph: Dict[str, Any]) -> str:
        """
        Build prompt for GraphRAG pipeline with minimal subgraph context
        
        Args:
            subgraph: Causal subgraph from TigerGraph traversal
            
        Returns:
            Complete prompt string
        """
        system_prompt = """You are an expert Site Reliability Engineer analyzing a production incident.
You have been provided with a verified causal graph subgraph showing the relationships between
alerts, services, deployments, and configuration changes.

IMPORTANT: Only reason about entities and relationships present in the provided graph.
Do not invent or assume relationships that are not explicitly shown."""
        
        # Format subgraph as structured context
        graph_context = PromptBuilder._format_subgraph(subgraph)
        
        user_prompt = f"""Analyze this incident using the causal graph:

{graph_context}

Based on this verified causal chain, provide:
1. Root cause (which ConfigChange caused the incident)
2. Affected services (from the graph traversal)
3. Teams that should be paged (teams owning affected services)
4. Recommended remediation"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    @staticmethod
    def _format_subgraph(subgraph: Dict[str, Any]) -> str:
        """Format subgraph into readable text context"""
        lines = ["CAUSAL GRAPH:"]
        lines.append("")
        
        # Format nodes
        lines.append("Nodes:")
        for node in subgraph.get("nodes", []):
            node_type = node.get("type", "Unknown")
            node_id = node.get("id", "")
            node_name = node.get("name", "")
            
            if node_type == "ConfigChange":
                lines.append(f"  - {node_type} {node_id}: {node.get('key')} changed from {node.get('old_value')} to {node.get('new_value')}")
            elif node_type == "Deployment":
                lines.append(f"  - {node_type} {node_id}: version {node.get('version')}")
            else:
                lines.append(f"  - {node_type} {node_id}: {node_name}")
        
        lines.append("")
        
        # Format edges
        lines.append("Relationships:")
        for edge in subgraph.get("edges", []):
            lines.append(f"  - {edge['from']} --[{edge['type']}]--> {edge['to']}")
        
        lines.append("")
        
        # Add unpaged teams
        if subgraph.get("unpaged_teams"):
            lines.append("Teams NOT YET PAGED:")
            for team in subgraph["unpaged_teams"]:
                lines.append(f"  - {team['name']}: {team['reason']}")
        
        return "\n".join(lines)
    
    @staticmethod
    def count_tokens_estimate(text: str) -> int:
        """
        Rough token count estimate (4 chars ≈ 1 token)
        For accurate counting, use tiktoken in production
        """
        return len(text) // 4


if __name__ == "__main__":
    # Test prompt building
    builder = PromptBuilder()
    
    # Test baseline prompt
    baseline_context = "Alert: High error rate in auth-svc\nLogs: [8000 tokens of logs here]..."
    baseline_prompt = builder.build_baseline_prompt(baseline_context)
    print(f"Baseline prompt tokens (estimate): {builder.count_tokens_estimate(baseline_prompt)}")
    
    # Test GraphRAG prompt
    subgraph = {
        "nodes": [
            {"type": "Alert", "id": "alert_1", "name": "High error rate"},
            {"type": "Service", "id": "svc_1", "name": "auth-svc"},
            {"type": "ConfigChange", "id": "config_3", "key": "JWT_EXPIRY_SECONDS", 
             "old_value": "3600", "new_value": "60"}
        ],
        "edges": [
            {"from": "alert_1", "to": "svc_1", "type": "fired_on"},
            {"from": "svc_1", "to": "config_3", "type": "changed_config"}
        ],
        "unpaged_teams": [
            {"name": "Payments", "reason": "Owns affected service"}
        ]
    }
    graphrag_prompt = builder.build_graphrag_prompt(subgraph)
    print(f"GraphRAG prompt tokens (estimate): {builder.count_tokens_estimate(graphrag_prompt)}")
    print(f"\nGraphRAG prompt:\n{graphrag_prompt}")

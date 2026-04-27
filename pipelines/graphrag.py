"""
GraphRAG Pipeline for PostMortemIQ
Processes incidents using TigerGraph traversal + minimal LLM context
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from graph.queries import GraphQueries
from llm.prompt_builder import PromptBuilder
from llm.groq_client import GroqClient
from llm.response_verifier import ResponseVerifier


class GraphRAGPipeline:
    """GraphRAG pipeline using graph traversal + LLM"""
    
    def __init__(self):
        self.graph_queries = GraphQueries()
        self.prompt_builder = PromptBuilder()
        self.llm_client = GroqClient()
        self.verifier = ResponseVerifier()
    
    def run(self, incident_id: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run GraphRAG pipeline on an incident
        
        Args:
            incident_id: The incident identifier
            incident_data: Incident information
            
        Returns:
            Pipeline result with RCA, tokens, latency, cost, hallucinations
        """
        import time
        start_time = time.time()
        
        # Step 1: Get causal subgraph from TigerGraph
        subgraph = self.graph_queries.get_causal_subgraph(incident_id)
        graph_latency_ms = int((time.time() - start_time) * 1000)
        
        # Step 2: Build minimal prompt from subgraph
        prompt = self.prompt_builder.build_graphrag_prompt(subgraph)
        
        # Step 3: Call LLM with minimal context
        llm_result = self.llm_client.call_llm(prompt)
        
        # Step 4: Verify response for hallucinations
        hallucination_report = self.verifier.detect_hallucinations(
            llm_result["response"],
            subgraph
        )
        
        # Calculate cost
        cost = self.llm_client.calculate_cost(
            llm_result["input_tokens"],
            llm_result["output_tokens"]
        )
        
        total_latency_ms = graph_latency_ms + llm_result["latency_ms"]
        
        return {
            "pipeline": "graphrag",
            "incident_id": incident_id,
            "rca_report": llm_result["response"],
            "input_tokens": llm_result["input_tokens"],
            "output_tokens": llm_result["output_tokens"],
            "total_tokens": llm_result["total_tokens"],
            "latency_ms": total_latency_ms,
            "graph_latency_ms": graph_latency_ms,
            "llm_latency_ms": llm_result["latency_ms"],
            "cost_usd": cost,
            "subgraph": subgraph,
            "hallucination_count": hallucination_report["hallucination_count"],
            "hallucination_rate": hallucination_report["hallucination_rate"],
            "hallucinated_entities": hallucination_report["hallucinated_entities"]
        }


if __name__ == "__main__":
    pipeline = GraphRAGPipeline()
    
    test_incident = {
        "incident_id": "incident_1",
        "alert_id": "alert_1",
        "alert_name": "High error rate in auth-svc",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z"
    }
    
    result = pipeline.run("incident_1", test_incident)
    print(f"GraphRAG Pipeline Result:")
    print(f"  Tokens: {result['total_tokens']}")
    print(f"  Latency: {result['latency_ms']}ms (graph: {result['graph_latency_ms']}ms, llm: {result['llm_latency_ms']}ms)")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Hallucinations: {result['hallucination_count']} ({result['hallucination_rate']:.1%})")

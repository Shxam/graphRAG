"""
Pipeline Comparator for PostMortemIQ
Compares baseline and GraphRAG pipeline results
"""

from typing import Dict, Any, Optional


class Comparator:
    """Compares baseline and GraphRAG pipeline results"""
    
    @staticmethod
    def compare(baseline_result: Dict[str, Any], 
                graphrag_result: Dict[str, Any],
                ground_truth: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compare two pipeline results
        
        Args:
            baseline_result: Result from baseline pipeline
            graphrag_result: Result from GraphRAG pipeline
            ground_truth: Optional ground truth for accuracy calculation
            
        Returns:
            Comparison metrics
        """
        # Token comparison
        token_delta = baseline_result["total_tokens"] - graphrag_result["total_tokens"]
        token_reduction_pct = (token_delta / baseline_result["total_tokens"]) * 100
        
        # Latency comparison
        latency_delta = baseline_result["latency_ms"] - graphrag_result["latency_ms"]
        latency_reduction_pct = (latency_delta / baseline_result["latency_ms"]) * 100
        
        # Cost comparison
        cost_delta = baseline_result["cost_usd"] - graphrag_result["cost_usd"]
        cost_savings_pct = (cost_delta / baseline_result["cost_usd"]) * 100
        
        # Accuracy comparison (if ground truth provided)
        accuracy_baseline = None
        accuracy_graphrag = None
        if ground_truth:
            accuracy_baseline = Comparator._check_accuracy(
                baseline_result["rca_report"],
                ground_truth
            )
            accuracy_graphrag = Comparator._check_accuracy(
                graphrag_result["rca_report"],
                ground_truth
            )
        
        # Hallucination comparison
        hallucination_delta = (
            graphrag_result.get("hallucination_rate", 0) - 
            baseline_result.get("hallucination_rate", 0)
        )
        
        return {
            "incident_id": baseline_result["incident_id"],
            
            # Token metrics
            "baseline_tokens": baseline_result["total_tokens"],
            "graphrag_tokens": graphrag_result["total_tokens"],
            "token_delta": token_delta,
            "token_reduction_pct": token_reduction_pct,
            
            # Latency metrics
            "baseline_latency_ms": baseline_result["latency_ms"],
            "graphrag_latency_ms": graphrag_result["latency_ms"],
            "latency_delta_ms": latency_delta,
            "latency_reduction_pct": latency_reduction_pct,
            
            # Cost metrics
            "baseline_cost_usd": baseline_result["cost_usd"],
            "graphrag_cost_usd": graphrag_result["cost_usd"],
            "cost_delta_usd": cost_delta,
            "cost_savings_pct": cost_savings_pct,
            
            # Accuracy metrics
            "accuracy_baseline": accuracy_baseline,
            "accuracy_graphrag": accuracy_graphrag,
            
            # Hallucination metrics
            "hallucination_rate_baseline": baseline_result.get("hallucination_rate", 0),
            "hallucination_rate_graphrag": graphrag_result.get("hallucination_rate", 0),
            "hallucination_delta": hallucination_delta,
            
            # Full results
            "baseline_result": baseline_result,
            "graphrag_result": graphrag_result
        }
    
    @staticmethod
    def _check_accuracy(rca_report: str, ground_truth: Dict[str, Any]) -> bool:
        """
        Check if RCA report correctly identifies ground truth root cause
        
        Args:
            rca_report: The LLM's RCA report
            ground_truth: Ground truth data
            
        Returns:
            True if root cause correctly identified
        """
        root_cause_id = ground_truth.get("ground_truth_root_cause", "")
        
        # Simple check: does the report mention the root cause ID?
        # In production, this would be more sophisticated
        return root_cause_id.lower() in rca_report.lower()
    
    @staticmethod
    def aggregate_results(comparisons: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate multiple comparison results for benchmark
        
        Args:
            comparisons: List of comparison results
            
        Returns:
            Aggregated metrics
        """
        if not comparisons:
            return {}
        
        n = len(comparisons)
        
        return {
            "total_incidents": n,
            "avg_token_reduction_pct": sum(c["token_reduction_pct"] for c in comparisons) / n,
            "avg_cost_savings_pct": sum(c["cost_savings_pct"] for c in comparisons) / n,
            "avg_latency_reduction_pct": sum(c["latency_reduction_pct"] for c in comparisons) / n,
            "total_cost_saved_usd": sum(c["cost_delta_usd"] for c in comparisons),
            "graphrag_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_graphrag")) / n if any(c.get("accuracy_graphrag") is not None for c in comparisons) else None,
            "baseline_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_baseline")) / n if any(c.get("accuracy_baseline") is not None for c in comparisons) else None,
            "avg_hallucination_rate_baseline": sum(c["hallucination_rate_baseline"] for c in comparisons) / n,
            "avg_hallucination_rate_graphrag": sum(c["hallucination_rate_graphrag"] for c in comparisons) / n
        }


if __name__ == "__main__":
    # Test comparison
    baseline = {
        "incident_id": "incident_1",
        "total_tokens": 11500,
        "latency_ms": 4200,
        "cost_usd": 0.0092,
        "rca_report": "The issue appears to be related to auth-svc...",
        "hallucination_rate": 0.23
    }
    
    graphrag = {
        "incident_id": "incident_1",
        "total_tokens": 380,
        "latency_ms": 890,
        "cost_usd": 0.0003,
        "rca_report": "Root cause: config_3 JWT_EXPIRY_SECONDS changed from 3600 to 60",
        "hallucination_rate": 0.02
    }
    
    ground_truth = {
        "ground_truth_root_cause": "config_3"
    }
    
    comparison = Comparator.compare(baseline, graphrag, ground_truth)
    print(f"Comparison Result:")
    print(f"  Token reduction: {comparison['token_reduction_pct']:.1f}%")
    print(f"  Cost savings: {comparison['cost_savings_pct']:.1f}%")
    print(f"  Latency reduction: {comparison['latency_reduction_pct']:.1f}%")
    print(f"  GraphRAG accuracy: {comparison['accuracy_graphrag']}")
    print(f"  Baseline accuracy: {comparison['accuracy_baseline']}")

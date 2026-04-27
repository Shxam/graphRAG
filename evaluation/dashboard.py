"""
Streamlit Dashboard for PostMortemIQ
Displays side-by-side comparison of baseline vs GraphRAG pipelines
"""

import streamlit as st
import requests
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="PostMortemIQ",
    page_icon="🔍",
    layout="wide"
)

# API endpoint
API_URL = "http://localhost:8000"


def get_health():
    """Get API health status"""
    try:
        response = requests.get(f"{API_URL}/health")
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_attestation():
    """Get TEE attestation report"""
    try:
        response = requests.get(f"{API_URL}/attest")
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def analyze_incident(incident_id):
    """Analyze an incident"""
    try:
        response = requests.post(
            f"{API_URL}/incident",
            json={"incident_id": incident_id}
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def run_benchmark():
    """Run full benchmark"""
    try:
        response = requests.get(f"{API_URL}/benchmark")
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# Header
st.title("🔍 PostMortemIQ")
st.subheader("GraphRAG Incident Root-Cause Engine with Trusted Execution Environment")

# TEE Status Bar
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    health = get_health()
    if health.get("status") == "healthy":
        st.success("✓ API: Healthy")
    else:
        st.error("✗ API: Unavailable")

with col2:
    attestation = get_attestation()
    if "mrenclave" in attestation:
        st.success(f"✓ TEE: Active")
    else:
        st.warning("⚠ TEE: Simulation")

with col3:
    if "mrenclave" in attestation:
        st.info(f"MRENCLAVE: {attestation['mrenclave'][:16]}...")

st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["🔥 Incident Analysis", "📊 Benchmark", "🔐 TEE Attestation"])

# Tab 1: Incident Analysis
with tab1:
    st.header("Incident Analysis")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        incident_id = st.text_input("Incident ID", value="incident_1", key="incident_input")
    with col2:
        st.write("")
        st.write("")
        analyze_button = st.button("🔍 Analyze Incident", type="primary")
    
    if analyze_button:
        with st.spinner("Analyzing incident..."):
            result = analyze_incident(incident_id)
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            # Aggregate Stats
            st.subheader("📈 Comparison Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Token Reduction",
                    f"{result['token_reduction_pct']:.1f}%",
                    f"-{result['token_delta']} tokens"
                )
            with col2:
                st.metric(
                    "Cost Savings",
                    f"{result['cost_savings_pct']:.1f}%",
                    f"-${result['cost_delta_usd']:.6f}"
                )
            with col3:
                st.metric(
                    "Latency Reduction",
                    f"{result['latency_reduction_pct']:.1f}%",
                    f"-{result['latency_delta_ms']}ms"
                )
            with col4:
                hallucination_improvement = (
                    result['hallucination_rate_baseline'] - 
                    result['hallucination_rate_graphrag']
                ) * 100
                st.metric(
                    "Hallucination Reduction",
                    f"{hallucination_improvement:.1f}%",
                    "Lower is better"
                )
            
            st.divider()
            
            # Side-by-side comparison
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔵 Baseline LLM")
                baseline = result['baseline_result']
                
                st.metric("Tokens", f"{baseline['total_tokens']:,}")
                st.metric("Latency", f"{baseline['latency_ms']}ms")
                st.metric("Cost", f"${baseline['cost_usd']:.6f}")
                
                if result.get('accuracy_baseline') is not None:
                    if result['accuracy_baseline']:
                        st.success("✓ Accuracy: Correct")
                    else:
                        st.error("✗ Accuracy: Incorrect")
                
                st.write("**RCA Report:**")
                st.text_area("Baseline Response", baseline['rca_report'], height=300, key="baseline_rca")
            
            with col2:
                st.subheader("🟢 GraphRAG (TigerGraph + LLM)")
                graphrag = result['graphrag_result']
                
                st.metric("Tokens", f"{graphrag['total_tokens']:,}")
                st.metric("Latency", f"{graphrag['latency_ms']}ms")
                st.metric("Cost", f"${graphrag['cost_usd']:.6f}")
                
                if result.get('accuracy_graphrag') is not None:
                    if result['accuracy_graphrag']:
                        st.success("✓ Accuracy: Correct")
                    else:
                        st.error("✗ Accuracy: Incorrect")
                
                st.write("**RCA Report:**")
                st.text_area("GraphRAG Response", graphrag['rca_report'], height=300, key="graphrag_rca")

# Tab 2: Benchmark
with tab2:
    st.header("📊 Benchmark Results")
    st.write("Run the full benchmark across all synthetic incidents")
    
    if st.button("▶ Run Full Benchmark", type="primary"):
        with st.spinner("Running benchmark... This may take a few minutes."):
            benchmark_result = run_benchmark()
        
        if "error" in benchmark_result:
            st.error(f"Error: {benchmark_result['error']}")
        else:
            aggregate = benchmark_result['benchmark_results']
            
            st.success(f"✓ Benchmark complete! Analyzed {aggregate['total_incidents']} incidents")
            
            # Aggregate metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Avg Token Reduction",
                    f"{aggregate['avg_token_reduction_pct']:.1f}%"
                )
            with col2:
                st.metric(
                    "Avg Cost Savings",
                    f"{aggregate['avg_cost_savings_pct']:.1f}%"
                )
            with col3:
                st.metric(
                    "Total Cost Saved",
                    f"${aggregate['total_cost_saved_usd']:.4f}"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                if aggregate.get('graphrag_accuracy_rate') is not None:
                    st.metric(
                        "GraphRAG Accuracy",
                        f"{aggregate['graphrag_accuracy_rate']*100:.1f}%"
                    )
            with col2:
                if aggregate.get('baseline_accuracy_rate') is not None:
                    st.metric(
                        "Baseline Accuracy",
                        f"{aggregate['baseline_accuracy_rate']*100:.1f}%"
                    )
            
            st.divider()
            
            # Individual results table
            st.subheader("Individual Incident Results")
            individual = benchmark_result['individual_results']
            
            table_data = []
            for r in individual:
                table_data.append({
                    "Incident": r['incident_id'],
                    "Token Reduction": f"{r['token_reduction_pct']:.1f}%",
                    "Cost Savings": f"{r['cost_savings_pct']:.1f}%",
                    "Latency Reduction": f"{r['latency_reduction_pct']:.1f}%",
                    "GraphRAG Accuracy": "✓" if r.get('accuracy_graphrag') else "✗"
                })
            
            st.dataframe(table_data, use_container_width=True)

# Tab 3: TEE Attestation
with tab3:
    st.header("🔐 TEE Attestation")
    st.write("Trusted Execution Environment status and attestation report")
    
    attestation = get_attestation()
    
    if "error" in attestation:
        st.error(f"Error: {attestation['error']}")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Attestation Report")
            st.json(attestation)
        
        with col2:
            st.subheader("Security Guarantees")
            st.write("""
            **Confidentiality**: Data is decrypted only inside the enclave
            
            **Integrity**: Code running inside is cryptographically verified
            
            **Attestation**: Any party can verify the correct code processed the data
            
            **Mode**: Simulation (for hackathon demo)
            
            **Production Path**: AWS Nitro Enclaves or Intel SGX hardware
            """)
            
            if "mrenclave" in attestation:
                st.info(f"**MRENCLAVE**: `{attestation['mrenclave']}`")
                st.caption("This hash uniquely identifies the code running inside the enclave")

# Footer
st.divider()
st.caption("PostMortemIQ - GraphRAG Incident Root-Cause Engine | Built for TigerGraph GraphRAG Hackathon")

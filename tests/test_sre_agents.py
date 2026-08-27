import pytest
from agents.pipeline_simulator import MediaPipelineSimulator
from agents.grafana_mcp_client import GrafanaMCPClient
from agents.gemini_sre_agent import GeminiSREAgent
from agents.remediation_engine import RemediationEngine

def test_pipeline_simulator_baseline_and_chaos():
    sim = MediaPipelineSimulator()
    metric = sim.tick()
    assert metric["p99_latency_ms"] < 100.0
    assert metric["error_rate_pct"] < 1.0

    # Inject Chaos
    inc = sim.inject_disaster("CDN_CACHE_POISONING")
    assert inc["status"] == "FIRING"
    assert sim.active_disaster is not None

    metric_disaster = sim.tick()
    assert metric_disaster["p99_latency_ms"] > 200.0
    assert metric_disaster["error_rate_pct"] > 5.0

def test_grafana_mcp_query_tools():
    sim = MediaPipelineSimulator()
    mcp = GrafanaMCPClient()
    
    prom_res = mcp.query_prometheus("rate(http_requests_total)[5m]", sim.history_metrics)
    assert prom_res["status"] == "success"
    assert prom_res["mcp_tool"] == "query_prometheus"

    loki_res = mcp.query_loki('{service="edge-cdn"} |= "error"', sim.logs_buffer)
    assert loki_res["status"] == "success"
    assert loki_res["mcp_tool"] == "query_loki"

def test_gemini_sre_agent_triage_and_self_healing():
    sim = MediaPipelineSimulator()
    mcp = GrafanaMCPClient()
    agent = GeminiSREAgent(mcp)
    engine = RemediationEngine(sim, mcp)

    sim.inject_disaster("CDN_CACHE_POISONING")
    triage = agent.run_incident_triage(sim.active_disaster, sim.history_metrics, sim.logs_buffer)

    assert triage["status"] == "INCIDENT_DIAGNOSED"
    assert "remediation_runbook" in triage
    assert triage["confidence_score"] > 80.0

    # Execute Remediation
    res = engine.execute_runbook(triage["remediation_runbook"], triage["incident_id"], triage["service"])
    assert res["status"] == "SUCCESS"
    assert sim.active_disaster is None
    assert sim.resolved_count == 1

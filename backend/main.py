"""
FastAPI Server & Autonomous Mission Control for DirectorGuard.AI
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import os
import asyncio

from agents.pipeline_simulator import MediaPipelineSimulator
from agents.grafana_mcp_client import GrafanaMCPClient
from agents.gemini_sre_agent import GeminiSREAgent
from agents.remediation_engine import RemediationEngine

app = FastAPI(title="DirectorGuard.AI - Autonomous Media SRE Swarm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Singletons
simulator = MediaPipelineSimulator()
mcp_client = GrafanaMCPClient()
sre_agent = GeminiSREAgent(mcp_client)
remediation_engine = RemediationEngine(simulator, mcp_client)

autonomous_healing_enabled = True

class ChaosInjectRequest(BaseModel):
    disaster_type: str = "CDN_CACHE_POISONING"

class RunbookExecuteRequest(BaseModel):
    incident_id: str
    runbook_name: str
    service: str

@app.get("/api/telemetry")
async def get_telemetry():
    # Update simulator tick
    latest = simulator.tick()
    triage = sre_agent.run_incident_triage(
        simulator.active_disaster,
        simulator.history_metrics,
        simulator.logs_buffer
    )
    
    # If autonomous mode is enabled and incident is firing, self-heal automatically
    auto_healed = False
    if autonomous_healing_enabled and simulator.active_disaster and triage.get("status") == "INCIDENT_DIAGNOSED":
        remediation_engine.execute_runbook(
            runbook_name=triage["remediation_runbook"],
            incident_id=triage["incident_id"],
            service=triage["service"]
        )
        auto_healed = True

    return {
        "latest_metric": latest,
        "history_metrics": simulator.history_metrics,
        "logs": simulator.logs_buffer[:25],
        "active_incident": simulator.active_disaster,
        "triage": triage,
        "autonomous_healing": autonomous_healing_enabled,
        "auto_healed_trigger": auto_healed,
        "resolved_incidents_count": simulator.resolved_count,
        "recent_audit": remediation_engine.audit_log[:5],
    }

@app.post("/api/chaos/inject")
async def inject_chaos(req: ChaosInjectRequest):
    inc = simulator.inject_disaster(req.disaster_type)
    return {"status": "DISASTER_INJECTED", "incident": inc}

@app.post("/api/remediation/execute")
async def execute_remediation(req: RunbookExecuteRequest):
    res = remediation_engine.execute_runbook(req.runbook_name, req.incident_id, req.service)
    return {"status": "SUCCESS", "result": res}

@app.post("/api/autonomous/toggle")
async def toggle_autonomous():
    global autonomous_healing_enabled
    autonomous_healing_enabled = not autonomous_healing_enabled
    return {"autonomous_healing": autonomous_healing_enabled}

@app.get("/api/mcp/tools")
async def get_mcp_tools():
    return {"tools": mcp_client.tool_inventory, "grafana_url": mcp_client.grafana_url}

# Mount frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

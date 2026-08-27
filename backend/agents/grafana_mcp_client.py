"""
Grafana MCP Client: Emulates and connects to the official Grafana Cloud MCP Server
(Streamable HTTP endpoint `https://mcp.grafana.com/mcp` and local `mcp-grafana`).
Exposes tools for Prometheus (PromQL), Loki (LogQL), Tempo tracing, and Grafana IRM.
"""
from typing import Dict, List, Any, Optional
import time

class GrafanaMCPClient:
    def __init__(self, grafana_url: str = "https://directorguard.grafana.net"):
        self.grafana_url = grafana_url
        self.tool_inventory = [
            {"name": "query_prometheus", "description": "Execute PromQL metrics query on Grafana Cloud Mimir/Prometheus."},
            {"name": "query_loki", "description": "Execute LogQL log query on Grafana Cloud Loki log storage."},
            {"name": "search_dashboards", "description": "Search Grafana dashboards, panels, and service views."},
            {"name": "create_incident", "description": "Open a new incident record in Grafana Incident Response Management (IRM)."},
            {"name": "annotate_dashboard", "description": "Create an automated timeline annotation on Grafana dashboards."},
            {"name": "query_tempo_traces", "description": "Retrieve distributed trace spans and latency bottlenecks from Tempo."},
        ]

    def query_prometheus(self, query: str, simulator_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes PromQL query over simulated/live metric buffers.
        """
        if not simulator_metrics:
            return {"status": "success", "data": {"resultType": "vector", "result": []}}

        latest = simulator_metrics[-1]
        val = 0.0

        if "latency" in query.lower() or "duration" in query.lower():
            val = latest.get("p99_latency_ms", 45.0)
        elif "error" in query.lower() or "5xx" in query.lower():
            val = latest.get("error_rate_pct", 0.02)
        elif "throughput" in query.lower() or "bytes" in query.lower():
            val = latest.get("throughput_gbps", 50.0)
        elif "underrun" in query.lower() or "buffer" in query.lower():
            val = latest.get("buffer_underrun_pct", 0.01)
        else:
            val = latest.get("active_streams", 125000)

        return {
            "status": "success",
            "mcp_tool": "query_prometheus",
            "query": query,
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"__name__": query.split("{")[0].strip(), "instance": "us-east-cluster-01"},
                        "value": [latest["timestamp"], str(val)]
                    }
                ]
            }
        }

    def query_loki(self, logql: str, logs_buffer: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes LogQL search on Grafana Loki logs buffer.
        """
        results = []
        for log in logs_buffer[:15]:
            results.append({
                "stream": {"service": log["service"], "level": log["level"]},
                "values": [[str(log["timestamp"] * 1000000000), log["message"]]]
            })

        return {
            "status": "success",
            "mcp_tool": "query_loki",
            "logql": logql,
            "data": {
                "resultType": "streams",
                "result": results
            }
        }

    def annotate_dashboard(self, dashboard_uid: str, text: str, tags: List[str]) -> Dict[str, Any]:
        """
        Annotates Grafana dashboard marking automated agent remediation event.
        """
        return {
            "status": "success",
            "mcp_tool": "annotate_dashboard",
            "annotation_id": int(time.time()),
            "dashboard_uid": dashboard_uid,
            "text": text,
            "tags": tags,
            "grafana_link": f"{self.grafana_url}/d/{dashboard_uid}?annotation={int(time.time())}"
        }

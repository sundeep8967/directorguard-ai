"""
Pipeline Simulator: Simulates a high-throughput Media & Entertainment video streaming,
transcoding, and CDN delivery infrastructure. Generates real-time Prometheus metrics
and Loki structured log streams.
"""
from typing import Dict, List, Any
import time
import random
import math

class MediaPipelineSimulator:
    def __init__(self):
        self.services = ["video-ingest", "transcoder-4k", "segmenter-hls", "edge-cdn-gateway", "auth-token-service"]
        self.active_disaster: Dict[str, Any] = None
        self.history_metrics: List[Dict[str, Any]] = []
        self.logs_buffer: List[Dict[str, Any]] = []
        self.incident_history: List[Dict[str, Any]] = []
        self.resolved_count = 0
        self._init_baseline()

    def _init_baseline(self):
        now = int(time.time())
        for i in range(30, 0, -1):
            t = now - (i * 5)
            self.history_metrics.append({
                "timestamp": t,
                "p99_latency_ms": round(random.uniform(42.0, 58.0), 1),
                "error_rate_pct": round(random.uniform(0.01, 0.08), 3),
                "throughput_gbps": round(random.uniform(48.0, 54.0), 1),
                "buffer_underrun_pct": round(random.uniform(0.0, 0.04), 2),
                "active_streams": random.randint(124000, 126000),
            })

    def inject_disaster(self, disaster_type: str) -> Dict[str, Any]:
        now = int(time.time())
        disasters = {
            "CDN_CACHE_POISONING": {
                "id": f"INC-{now}",
                "title": "High Latency & 502 Spikes across Edge CDN Nodes",
                "service": "edge-cdn-gateway",
                "severity": "CRITICAL (P1)",
                "description": "Corrupted HLS video segment manifests triggering 502 Bad Gateway errors and client rebuffering across US-East CDN edges.",
                "remediation_runbook": "PURGE_CDN_CACHE_AND_REROUTE",
                "target_metric": "p99_latency_ms",
            },
            "TRANSCODER_OOM_STALL": {
                "id": f"INC-{now}",
                "title": "4K HDR Transcoding Cluster Queue Starvation (OOM Kill)",
                "service": "transcoder-4k",
                "severity": "HIGH (P2)",
                "description": "HEVC encoder memory leak causing worker pod eviction and queue backlog accumulation.",
                "remediation_runbook": "AUTOSCALE_AND_ROLLBACK_CANARY",
                "target_metric": "buffer_underrun_pct",
            },
            "AUTH_RATE_LIMIT_DEADLOCK": {
                "id": f"INC-{now}",
                "title": "DRM Token Verification Timeout Cascades",
                "service": "auth-token-service",
                "severity": "CRITICAL (P1)",
                "description": "Redis connection pool exhaustion causing playback authentication stalls for live broadcast viewers.",
                "remediation_runbook": "EXPAND_CONNECTION_POOL_AND_CIRCUIT_BREAK",
                "target_metric": "error_rate_pct",
            }
        }

        self.active_disaster = disasters.get(disaster_type, disasters["CDN_CACHE_POISONING"])
        self.active_disaster["injected_at"] = now
        self.active_disaster["status"] = "FIRING"
        self.incident_history.insert(0, self.active_disaster)

        # Inject immediate high-severity log
        self.logs_buffer.insert(0, {
            "timestamp": now,
            "service": self.active_disaster["service"],
            "level": "FATAL",
            "message": f"ALERT [Prometheus/Alertmanager] {self.active_disaster['title']}: {self.active_disaster['description']}",
        })

        return self.active_disaster

    def resolve_disaster(self, action: str) -> Dict[str, Any]:
        if not self.active_disaster:
            return {"status": "NO_ACTIVE_INCIDENT"}

        now = int(time.time())
        resolved_inc = self.active_disaster
        resolved_inc["status"] = "RESOLVED"
        resolved_inc["resolved_at"] = now
        resolved_inc["remediation_action_taken"] = action
        
        self.active_disaster = None
        self.resolved_count += 1

        self.logs_buffer.insert(0, {
            "timestamp": now,
            "service": resolved_inc["service"],
            "level": "INFO",
            "message": f"REMEDIATION SUCCESS: Executed {action}. System returning to baseline SLI thresholds.",
        })

        return {"status": "RESOLVED", "incident": resolved_inc}

    def tick(self) -> Dict[str, Any]:
        now = int(time.time())
        
        # Determine baseline vs disaster values
        if self.active_disaster:
            lat = round(random.uniform(420.0, 780.0), 1)
            err = round(random.uniform(14.5, 28.2), 2)
            thru = round(random.uniform(22.0, 31.0), 1)
            underrun = round(random.uniform(8.4, 16.8), 2)
            streams = random.randint(95000, 105000)
            
            # Emit error logs
            log_msgs = [
                f"[502 Gateway Error] upstream edge connection timeout in {self.active_disaster['service']}",
                f"[HLS Segment Fetch Failed] chunk_720p_00492.ts returned error status 503",
                f"[High Latency SLI Breached] P99 response time is {lat}ms (> 100ms threshold)",
            ]
            self.logs_buffer.insert(0, {
                "timestamp": now,
                "service": self.active_disaster["service"],
                "level": "ERROR",
                "message": random.choice(log_msgs),
            })
        else:
            lat = round(random.uniform(42.0, 56.0), 1)
            err = round(random.uniform(0.01, 0.06), 3)
            thru = round(random.uniform(49.0, 55.0), 1)
            underrun = round(random.uniform(0.0, 0.03), 2)
            streams = random.randint(125000, 127000)

            if random.random() < 0.35:
                self.logs_buffer.insert(0, {
                    "timestamp": now,
                    "service": random.choice(self.services),
                    "level": "INFO",
                    "message": f"Successfully processed stream batch (codec=h265, bitrate=8500kbps, latency={lat}ms)",
                })

        new_metric = {
            "timestamp": now,
            "p99_latency_ms": lat,
            "error_rate_pct": err,
            "throughput_gbps": thru,
            "buffer_underrun_pct": underrun,
            "active_streams": streams,
        }
        self.history_metrics.append(new_metric)
        if len(self.history_metrics) > 60:
            self.history_metrics.pop(0)

        if len(self.logs_buffer) > 100:
            self.logs_buffer.pop()

        return new_metric

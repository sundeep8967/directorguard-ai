// DirectorGuard.AI Frontend Application Logic
let autonomousHealing = true;
let metricHistory = [];

const sliP99El = document.getElementById("sliP99");
const sliErrEl = document.getElementById("sliErr");
const sliStreamsEl = document.getElementById("sliStreams");
const sliThruEl = document.getElementById("sliThru");

const incidentCard = document.getElementById("incidentCard");
const incidentBadge = document.getElementById("incidentBadge");
const incidentIdEl = document.getElementById("incidentId");
const incidentTitleEl = document.getElementById("incidentTitle");
const incidentDescEl = document.getElementById("incidentDesc");
const remediationBox = document.getElementById("remediationBox");
const remTitleEl = document.getElementById("remTitle");
const manualExecuteBtn = document.getElementById("manualExecuteBtn");

const toggleAutonomousBtn = document.getElementById("toggleAutonomousBtn");
const autonomousText = document.getElementById("autonomousText");
const chaosButtons = document.querySelectorAll(".chaos-btn");

const reasoningFeed = document.getElementById("reasoningFeed");
const lokiTerminal = document.getElementById("lokiTerminal");

const canvas = document.getElementById("telemetryCanvas");
const ctx = canvas.getContext("2d");

window.addEventListener("DOMContentLoaded", () => {
    initChaosTriggers();
    initAutonomousToggle();
    pollTelemetry();
    setInterval(pollTelemetry, 2500);
});

function initChaosTriggers() {
    chaosButtons.forEach(btn => {
        btn.addEventListener("click", async () => {
            const disaster_type = btn.getAttribute("data-disaster");
            btn.style.opacity = "0.5";
            try {
                await fetch("/api/chaos/inject", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ disaster_type })
                });
                pollTelemetry();
            } catch (e) {
                console.error("Chaos injection error:", e);
            } finally {
                btn.style.opacity = "1";
            }
        });
    });
}

function initAutonomousToggle() {
    toggleAutonomousBtn.addEventListener("click", async () => {
        const res = await fetch("/api/autonomous/toggle", { method: "POST" });
        const data = await res.json();
        autonomousHealing = data.autonomous_healing;
        if (autonomousHealing) {
            toggleAutonomousBtn.classList.add("active");
            autonomousText.textContent = "Auto-Remediation: ON";
        } else {
            toggleAutonomousBtn.classList.remove("active");
            autonomousText.textContent = "Auto-Remediation: OFF";
        }
    });
}

async function pollTelemetry() {
    try {
        const res = await fetch("/api/telemetry");
        const data = await res.json();

        // Update SLI Gauges
        const latest = data.latest_metric;
        sliP99El.textContent = `${latest.p99_latency_ms} ms`;
        sliErrEl.textContent = `${latest.error_rate_pct}%`;
        sliStreamsEl.textContent = latest.active_streams.toLocaleString();
        sliThruEl.textContent = `${latest.throughput_gbps} Gbps`;

        // Color coding
        if (latest.p99_latency_ms > 100) {
            sliP99El.style.color = "var(--accent-rose)";
            sliErrEl.style.color = "var(--accent-rose)";
        } else {
            sliP99El.style.color = "var(--accent-emerald)";
            sliErrEl.style.color = "var(--accent-emerald)";
        }

        // Active Incident
        if (data.active_incident && data.active_incident.status === "FIRING") {
            incidentCard.className = "card incident-card firing";
            incidentBadge.className = "status-badge firing";
            incidentBadge.textContent = `🔴 ALERT: ${data.active_incident.severity}`;
            incidentIdEl.textContent = data.active_incident.id;
            incidentTitleEl.textContent = data.active_incident.title;
            incidentDescEl.textContent = data.active_incident.description;

            remediationBox.style.display = "flex";
            remTitleEl.textContent = data.active_incident.remediation_runbook;

            // Highlight degraded topology node
            document.querySelectorAll(".service-node").forEach(n => n.classList.remove("degraded"));
            const targetNode = document.getElementById(`node-${data.active_incident.service}`);
            if (targetNode) {
                targetNode.classList.add("degraded");
                targetNode.querySelector(".node-status").textContent = "CRITICAL 502";
            }
        } else {
            incidentCard.className = "card incident-card";
            incidentBadge.className = "status-badge healthy";
            incidentBadge.textContent = "🟢 SYSTEM OPERATIONAL (100% SLI)";
            incidentIdEl.textContent = `RESOLVED (${data.resolved_incidents_count} TOTAL HEALED)`;
            incidentTitleEl.textContent = "All Media & Transcoding Ingestion Services Operating Within Baseline";
            incidentDescEl.textContent = "Prometheus metrics and Loki log streams indicate zero active production anomalies.";
            remediationBox.style.display = "none";

            document.querySelectorAll(".service-node").forEach(n => {
                n.classList.remove("degraded");
                n.querySelector(".node-status").textContent = "HEALTHY";
            });
        }

        // Gemini Reasoning Feed
        const triage = data.triage;
        if (triage.reasoning_trace) {
            reasoningFeed.innerHTML = triage.reasoning_trace.map(r => `
                <div class="reasoning-item">
                    ${r}
                </div>
            `).join("");
        } else if (triage.reasoning_steps) {
            reasoningFeed.innerHTML = triage.reasoning_steps.map(r => `
                <div class="reasoning-item">
                    <strong>✅ Grafana MCP Health Check:</strong> ${r}
                </div>
            `).join("");
        }

        // Loki Log Terminal
        lokiTerminal.innerHTML = data.logs.map(l => {
            const cls = l.level === "ERROR" ? "error" : (l.level === "FATAL" ? "fatal" : "info");
            return `<div class="log-line ${cls}">[${new Date(l.timestamp * 1000).toLocaleTimeString()}] [${l.service}] ${l.message}</div>`;
        }).join("");

        metricHistory = data.history_metrics;
        renderTelemetryChart(metricHistory);

    } catch (e) {
        console.error("Error polling telemetry:", e);
    }
}

manualExecuteBtn.addEventListener("click", async () => {
    try {
        manualExecuteBtn.disabled = true;
        manualExecuteBtn.textContent = "Executing...";
        const runbook = remTitleEl.textContent;
        const incId = incidentIdEl.textContent;
        await fetch("/api/remediation/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ incident_id: incId, runbook_name: runbook, service: "edge-cdn-gateway" })
        });
        pollTelemetry();
    } catch (e) {
        console.error("Manual execution error:", e);
    } finally {
        manualExecuteBtn.disabled = false;
        manualExecuteBtn.textContent = "Execute Runbook Now";
    }
});

function renderTelemetryChart(metrics) {
    if (!metrics || metrics.length === 0) return;
    const width = canvas.width = canvas.parentElement.clientWidth;
    const height = canvas.height = canvas.parentElement.clientHeight;

    ctx.clearRect(0, 0, width, height);

    const padding = 25;
    const chartHeight = height - padding * 2;
    const chartWidth = width - padding * 2;

    const latencies = metrics.map(m => m.p99_latency_ms);
    const maxLat = Math.max(120.0, Math.max(...latencies) * 1.15);

    // Draw baseline threshold line (100ms)
    const thresholdY = padding + chartHeight * (1 - (100.0 / maxLat));
    ctx.strokeStyle = "rgba(244, 63, 94, 0.4)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padding, thresholdY);
    ctx.lineTo(width - padding, thresholdY);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "rgba(244, 63, 94, 0.7)";
    ctx.font = "9px JetBrains Mono";
    ctx.fillText("SLI Breach Limit (100ms)", width - padding - 130, thresholdY - 4);

    // Draw P99 Latency curve
    ctx.strokeStyle = "#06b6d4";
    ctx.lineWidth = 2;
    ctx.beginPath();
    metrics.forEach((m, idx) => {
        const x = padding + (idx / (metrics.length - 1)) * chartWidth;
        const y = padding + chartHeight * (1 - (m.p99_latency_ms / maxLat));
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Area fill
    ctx.lineTo(width - padding, height - padding);
    ctx.lineTo(padding, height - padding);
    ctx.fillStyle = "rgba(6, 182, 212, 0.08)";
    ctx.fill();
}

import React, { useState, useEffect, useRef } from "react";
import "../spawn.css";


const API = "http://localhost:8001";
const WS_BASE = "ws://localhost:8001/api/v1/ws/spawn";

const STATUS_COLOR = {
  pending:   "#f59e0b",
  claimed:   "#3b82f6",
  running:   "#8b5cf6",
  completed: "#10b981",
  failed:    "#ef4444",
  idle:      "#6b7280",
  busy:      "#8b5cf6",
  online:    "#10b981",
  offline:   "#6b7280",
};

const ROLE_EMOJI = {
  researcher:     "🔍",
  designer:       "🎨",
  writer:         "✍️",
  marketer:       "📣",
  analyst:        "📊",
  developer:      "💻",
  accountant:     "💰",
  manager:        "🎯",
  strategist:     "🧠",
  publisher:      "📤",
  customer_support: "💬",
  seo:            "🔎",
  default:        "🤖",
};

function getRoleEmoji(role) {
  const key = Object.keys(ROLE_EMOJI).find(k => role?.toLowerCase().includes(k));
  return key ? ROLE_EMOJI[key] : ROLE_EMOJI.default;
}

// ── Animated typing placeholder ─────────────────────────────────────────────
const EXAMPLES = [
  "Run a YouTube channel about AI tools",
  "Start a dropshipping business selling fitness gear",
  "Manage my Etsy shop with handmade jewelry",
  "Build and grow a SaaS landing page email list",
  "Research and launch a digital product on Gumroad",
  "Run a newsletter on tech trends",
  "Manage my Shopify store for clothing",
];

function useCyclingPlaceholder() {
  const [idx, setIdx] = useState(0);
  const [displayed, setDisplayed] = useState("");
  const [typing, setTyping] = useState(true);

  useEffect(() => {
    const target = EXAMPLES[idx];
    let timeout;
    if (typing) {
      if (displayed.length < target.length) {
        timeout = setTimeout(() => setDisplayed(target.slice(0, displayed.length + 1)), 40);
      } else {
        timeout = setTimeout(() => setTyping(false), 2000);
      }
    } else {
      if (displayed.length > 0) {
        timeout = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 20);
      } else {
        setIdx((i) => (i + 1) % EXAMPLES.length);
        setTyping(true);
      }
    }
    return () => clearTimeout(timeout);
  }, [displayed, typing, idx]);

  return displayed;
}

// ── Components ───────────────────────────────────────────────────────────────

function AgentCard({ agent, isNew }) {
  return (
    <div className={`agent-card ${isNew ? "agent-card--new" : ""}`}>
      <div className="agent-avatar">
        {getRoleEmoji(agent.role)}
      </div>
      <div className="agent-info">
        <div className="agent-name">{agent.name}</div>
        <div className="agent-role">{agent.role}</div>
        <div className="agent-caps">
          {(agent.capabilities || []).slice(0, 3).map(c => (
            <span key={c} className="cap-badge">{c.replace(/_/g, " ")}</span>
          ))}
        </div>
      </div>
      <div
        className="agent-status-dot"
        style={{ background: STATUS_COLOR[agent.status] || "#6b7280" }}
        title={agent.status}
      />
    </div>
  );
}

function TaskCard({ task }) {
  return (
    <div className="task-card">
      <div className="task-header">
        <span className="task-title">{task.title}</span>
        <span
          className="task-status"
          style={{ color: STATUS_COLOR[task.status] || "#fff" }}
        >
          {task.status}
        </span>
      </div>
      <div className="task-type">{task.task_type}</div>
      {task.output && (
        <div className="task-output">{task.output}</div>
      )}
    </div>
  );
}

function LiveEvent({ event }) {
  const icons = {
    task_started:   "⚡",
    task_completed: "✅",
    agent_message:  "💬",
    connected:      "🔗",
    default:        "📡",
  };
  const icon = icons[event.type] || icons.default;
  return (
    <div className="live-event">
      <span className="live-event-icon">{icon}</span>
      <div className="live-event-body">
        <span className="live-event-type">{event.type}</span>
        <span className="live-event-msg">
          {event.content || event.output || event.task_title || event.room_name || ""}
        </span>
        {event.agent_name && (
          <span className="live-event-agent">by {event.agent_name}</span>
        )}
      </div>
      <span className="live-event-time">
        {new Date(event.timestamp || Date.now()).toLocaleTimeString()}
      </span>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SpawnPage() {
  const placeholder        = useCyclingPlaceholder();
  const [goal, setGoal]    = useState("");
  const [phase, setPhase]  = useState("idle"); // idle | spawning | live
  const [spawnResult, setSpawnResult] = useState(null);
  const [roomDetail, setRoomDetail]   = useState(null);
  const [liveEvents, setLiveEvents]   = useState([]);
  const [error, setError]  = useState("");
  const wsRef              = useRef(null);
  const eventsEndRef       = useRef(null);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveEvents]);

  // ── Spawn ──
  async function handleSpawn() {
    if (!goal.trim()) return;
    setError("");
    setPhase("spawning");
    setLiveEvents([]);
    setRoomDetail(null);

    try {
      const res = await fetch(`${API}/api/v1/spawn`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ goal: goal.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Spawn failed");
      }

      const data = await res.json();
      setSpawnResult(data);
      setPhase("live");
      fetchRoomDetail(data.room_id);
      connectWs(data.room_id);
    } catch (e) {
      setError(e.message);
      setPhase("idle");
    }
  }

  // ── Fetch room detail ──
  async function fetchRoomDetail(roomId) {
    try {
      const res = await fetch(`${API}/api/v1/rooms/${roomId}`);
      if (res.ok) setRoomDetail(await res.json());
    } catch (e) { /* ignore */ }
  }

  // ── WebSocket ──
  function connectWs(roomId) {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(`${WS_BASE}/${roomId}`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const evt = JSON.parse(e.data);
      setLiveEvents(prev => [...prev.slice(-99), { ...evt, timestamp: evt.timestamp || new Date().toISOString() }]);

      // Refresh room detail on task events
      if (["task_completed", "task_started"].includes(evt.type)) {
        fetchRoomDetail(roomId);
      }
    };

    ws.onerror = () => setError("WebSocket connection lost. Events may be delayed.");
  }

  // ── Reset ──
  function handleReset() {
    if (wsRef.current) wsRef.current.close();
    setPhase("idle");
    setGoal("");
    setSpawnResult(null);
    setRoomDetail(null);
    setLiveEvents([]);
    setError("");
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="spawn-page">
      {/* ── Header ── */}
      <header className="spawn-header">
        <div className="spawn-logo">
          <span className="spawn-logo-icon">⚡</span>
          <span className="spawn-logo-text">Agent World</span>
        </div>
        <p className="spawn-tagline">
          Describe any business goal — watch your AI team build it.
        </p>
      </header>

      {/* ── Input Phase ── */}
      {phase === "idle" && (
        <section className="spawn-input-section">
          <div className="spawn-input-wrapper">
            <textarea
              className="spawn-textarea"
              value={goal}
              onChange={e => setGoal(e.target.value)}
              placeholder={placeholder || "What do you want agents to do?"}
              rows={3}
              onKeyDown={e => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSpawn();
              }}
            />
            <button
              className="spawn-btn"
              onClick={handleSpawn}
              disabled={!goal.trim()}
            >
              <span>Spawn Agents</span>
              <span className="spawn-btn-icon">🚀</span>
            </button>
          </div>
          {error && <div className="spawn-error">{error}</div>}
          <p className="spawn-hint">Press Ctrl+Enter to spawn · Supports any goal</p>
        </section>
      )}

      {/* ── Spawning Spinner ── */}
      {phase === "spawning" && (
        <section className="spawn-loading">
          <div className="spawn-spinner" />
          <p className="spawn-loading-text">Planning your agent team…</p>
          <p className="spawn-loading-sub">LLM is designing roles, prompts, and tasks</p>
        </section>
      )}

      {/* ── Live Dashboard ── */}
      {phase === "live" && spawnResult && (
        <section className="spawn-dashboard">
          {/* Goal bar */}
          <div className="goal-bar">
            <span className="goal-label">Goal:</span>
            <span className="goal-text">{goal}</span>
            <button className="reset-btn" onClick={handleReset}>↩ New Goal</button>
          </div>

          {/* Stats row */}
          <div className="stats-row">
            <div className="stat-card">
              <div className="stat-num">{spawnResult.agent_count}</div>
              <div className="stat-lbl">Agents Spawned</div>
            </div>
            <div className="stat-card">
              <div className="stat-num">{spawnResult.task_count}</div>
              <div className="stat-lbl">Tasks Seeded</div>
            </div>
            <div className="stat-card">
              <div className="stat-num" style={{ color: "#10b981" }}>
                {roomDetail?.tasks?.filter(t => t.status === "completed").length ?? 0}
              </div>
              <div className="stat-lbl">Completed</div>
            </div>
            <div className="stat-card">
              <div className="stat-num" style={{ color: "#8b5cf6" }}>
                {roomDetail?.tasks?.filter(t => t.status === "running").length ?? 0}
              </div>
              <div className="stat-lbl">Running</div>
            </div>
          </div>

          {/* Main grid */}
          <div className="dashboard-grid">
            {/* Agents */}
            <div className="dash-panel">
              <h3 className="panel-title">🤖 Agent Team</h3>
              <div className="agents-list">
                {(roomDetail?.agents || spawnResult.agents_created || []).map(ag => (
                  <AgentCard key={ag.id} agent={ag} />
                ))}
              </div>
            </div>

            {/* Tasks */}
            <div className="dash-panel">
              <h3 className="panel-title">📋 Task Queue</h3>
              <div className="tasks-list">
                {(roomDetail?.tasks || spawnResult.tasks_seeded || []).map((t, i) => (
                  <TaskCard key={t.id || i} task={t} />
                ))}
              </div>
            </div>

            {/* Live Events */}
            <div className="dash-panel dash-panel--events">
              <h3 className="panel-title">
                📡 Live Feed
                <span className="live-dot" />
              </h3>
              <div className="events-scroll">
                {liveEvents.length === 0 && (
                  <div className="events-empty">Waiting for agent activity…</div>
                )}
                {liveEvents.map((evt, i) => (
                  <LiveEvent key={i} event={evt} />
                ))}
                <div ref={eventsEndRef} />
              </div>
            </div>
          </div>

          {error && <div className="spawn-error">{error}</div>}
        </section>
      )}
    </div>
  );
}

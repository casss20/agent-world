import React, { useEffect, useState, useCallback } from 'react';

const API = import.meta.env.VITE_API_URL || '';

const ROLE_COLORS = {
  orchestrator:   '#00f3ff',
  researcher:     '#8b5cf6',
  designer:       '#ff006e',
  listing_builder:'#f59e0b',
  communications: '#10b981',
};

const ROLE_LABELS = {
  orchestrator:    'Orchestrator',
  researcher:      'Research',
  designer:        'Creative',
  listing_builder: 'Listing Builder',
  communications:  'Communications',
};

// ── Agent Template Card ─────────────────────────────────────────────────────
function AgentCard({ template, onSpawn }) {
  const [spawning, setSpawning] = useState(false);
  const [result,   setResult]   = useState(null);
  const color = ROLE_COLORS[template.role] || '#00f3ff';

  const handleSpawn = async () => {
    setSpawning(true);
    setResult(null);
    const r = await onSpawn(template.slug);
    setResult(r);
    setSpawning(false);
  };

  return (
    <div className="at-card glass-card" style={{ '--agent-color': color }}>
      {/* Accent line at top */}
      <div className="at-accent" style={{ background: `linear-gradient(90deg, ${color}, transparent)` }} />

      {/* Icon + name */}
      <div className="at-head">
        <div className="at-avatar" style={{ background: `rgba(${hexToRgb(color)}, 0.12)`, border: `1px solid rgba(${hexToRgb(color)}, 0.3)` }}>
          <span className="at-icon">{template.icon}</span>
        </div>
        <div className="at-identity">
          <span className="at-role-badge" style={{ color, borderColor: `rgba(${hexToRgb(color)}, 0.3)`, background: `rgba(${hexToRgb(color)}, 0.08)` }}>
            {ROLE_LABELS[template.role] || template.role}
          </span>
          <h3 className="at-name">{template.name}</h3>
        </div>
      </div>

      {/* Description */}
      <p className="at-desc">{template.description}</p>

      {/* Output types */}
      <div className="at-section">
        <span className="at-section-title">Produces</span>
        <div className="at-tags">
          {template.output_types.map(o => (
            <span key={o} className="at-tag at-tag--output">{o}</span>
          ))}
        </div>
      </div>

      {/* Capabilities */}
      <div className="at-section">
        <span className="at-section-title">Tools</span>
        <div className="at-tags">
          {template.capabilities.map(c => (
            <span key={c} className="at-tag">{c.replace(/_/g, ' ')}</span>
          ))}
        </div>
      </div>

      {/* Approval rules */}
      <div className="at-rules">
        <div className="at-rule at-rule--auto">
          <span className="at-rule-icon">⚡</span>
          <div>
            <span className="at-rule-label">Autonomous</span>
            <div className="at-rule-items">
              {template.autonomous_allowed.map(a => (
                <span key={a} className="at-rule-item">{a.replace(/_/g, ' ')}</span>
              ))}
            </div>
          </div>
        </div>
        {template.approval_required_for.length > 0 && (
          <div className="at-rule at-rule--block">
            <span className="at-rule-icon">🔒</span>
            <div>
              <span className="at-rule-label">Needs Approval</span>
              <div className="at-rule-items">
                {template.approval_required_for.map(a => (
                  <span key={a} className="at-rule-item at-rule-item--warn">{a.replace(/_/g, ' ')}</span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className={`at-result ${result.ok ? 'at-result--ok' : 'at-result--err'}`}>
          {result.ok
            ? `✓ ${result.created ? 'Spawned' : 'Already running'} — ${result.agent?.name}`
            : `✗ ${result.detail || 'Error'}`}
        </div>
      )}

      {/* Spawn button */}
      <button
        id={`spawn-${template.slug}`}
        className="at-spawn-btn"
        style={{ '--btn-color': color }}
        onClick={handleSpawn}
        disabled={spawning}
      >
        {spawning ? 'Spawning…' : `Spawn ${template.name}`}
      </button>
    </div>
  );
}

// ── Helper ──────────────────────────────────────────────────────────────────
function hexToRgb(hex) {
  const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return r ? `${parseInt(r[1],16)}, ${parseInt(r[2],16)}, ${parseInt(r[3],16)}` : '0,243,255';
}

// ── Architecture diagram (static) ──────────────────────────────────────────
function ArchDiagram() {
  return (
    <div className="arch-diagram glass">
      <h2 className="arch-title">How agents connect to channels</h2>
      <div className="arch-flow">
        {[
          { icon: '🤖', label: 'Agents produce outputs\n(Nova/Forge/Pixel/Cipher/Ultron)', type: 'agent' },
          { icon: '→', label: '', type: 'arrow' },
          { icon: '⚖️', label: 'Ledger Router evaluates\nrisk + finds channel', type: 'ledger' },
          { icon: '→', label: '', type: 'arrow' },
          { icon: '🔔', label: 'Hard outputs held\nfor human approval', type: 'approval' },
          { icon: '→', label: '', type: 'arrow' },
          { icon: '🚀', label: 'Approved outputs pushed\nto connected channel', type: 'channel' },
        ].map((s, i) => (
          <div key={i} className={`arch-step arch-step--${s.type}`}>
            <span className="arch-step-icon">{s.icon}</span>
            {s.label && <span className="arch-step-label">{s.label}</span>}
          </div>
        ))}
      </div>
      <p className="arch-note">
        Agents are <strong>platform-agnostic</strong> — swap Shopify for Etsy, or add Gumroad, without changing a single agent prompt.
      </p>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────
export default function AgentTemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [loading,   setLoading]   = useState(true);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/agent-templates`);
      if (r.ok) setTemplates((await r.json()).templates || []);
    } catch (e) {
      console.error('Template fetch failed:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  const handleSpawn = async (slug) => {
    try {
      const r = await fetch(`${API}/api/v1/agent-templates/${slug}/spawn`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({}),
      });
      return await r.json();
    } catch (e) {
      return { ok: false, detail: String(e) };
    }
  };

  return (
    <div className="at-page">
      {/* ── Hero ── */}
      <div className="at-hero">
        <div className="at-hero-inner">
          <div className="at-hero-icon">🧠</div>
          <div>
            <h1 className="at-page-title">Named Agents</h1>
            <p className="at-page-sub">
              Five purpose-built agents — spawn them once, they work for any platform.
            </p>
          </div>
          <div className="at-hero-badge">
            <span className="at-badge-text">{templates.length} templates</span>
          </div>
        </div>
      </div>

      <div className="at-body">
        {/* Architecture */}
        <ArchDiagram />

        {/* Template grid */}
        {loading ? (
          <div className="at-loading">
            <div className="at-spinner" />
            <p>Loading agent templates…</p>
          </div>
        ) : (
          <div className="at-grid">
            {templates.map(t => (
              <AgentCard key={t.slug} template={t} onSpawn={handleSpawn} />
            ))}
          </div>
        )}
      </div>

      <style>{`
        .at-page {
          min-height: 100vh;
          background:
            radial-gradient(ellipse 70% 50% at 10%  5%,  rgba(139,92,246,0.06)  0%, transparent 55%),
            radial-gradient(ellipse 60% 50% at 90% 80%,  rgba(0,243,255,0.05)   0%, transparent 55%),
            radial-gradient(ellipse 50% 40% at 50% 40%,  rgba(255,0,110,0.04)   0%, transparent 50%),
            #050a14;
          color: #e0e1dd;
          font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        }
        .at-hero {
          border-bottom: 1px solid rgba(139,92,246,0.15);
          background: rgba(0,15,30,0.6);
          backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
          padding: 2.5rem 2rem;
        }
        .at-hero-inner { max-width: 1100px; margin: 0 auto; display: flex; align-items: center; gap: 1.5rem; }
        .at-hero-icon { font-size: 3rem; filter: drop-shadow(0 0 16px rgba(139,92,246,0.7)); }
        .at-page-title {
          font-family: 'Orbitron', monospace; font-size: 1.7rem; font-weight: 700; margin: 0 0 0.25rem;
          background: linear-gradient(135deg, #8b5cf6, #00f3ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .at-page-sub { color: #64748b; margin: 0; font-size: 0.95rem; }
        .at-hero-badge { margin-left: auto; }
        .at-badge-text {
          font-family: 'Orbitron', monospace; font-size: 0.8rem; font-weight: 700;
          color: #8b5cf6; background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.25);
          padding: 0.4rem 0.9rem; border-radius: 20px;
        }

        .at-body { max-width: 1100px; margin: 0 auto; padding: 2rem; display: flex; flex-direction: column; gap: 1.75rem; }

        /* Architecture */
        .arch-diagram { border-radius: 14px; padding: 1.5rem; }
        .arch-title { font-family: 'Orbitron', monospace; font-size: 0.82rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 1rem; }
        .arch-flow { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
        .arch-step {
          display: flex; flex-direction: column; align-items: center; gap: 0.4rem;
          padding: 0.75rem 1rem; border-radius: 10px; flex: 1; min-width: 120px; text-align: center;
        }
        .arch-step--arrow { flex: 0; font-size: 1.4rem; color: #334155; padding: 0; min-width: auto; }
        .arch-step--agent    { background: rgba(0,243,255,0.05); border: 1px solid rgba(0,243,255,0.15); }
        .arch-step--ledger   { background: rgba(139,92,246,0.05); border: 1px solid rgba(139,92,246,0.15); }
        .arch-step--approval { background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.15); }
        .arch-step--channel  { background: rgba(16,185,129,0.05); border: 1px solid rgba(16,185,129,0.15); }
        .arch-step-icon { font-size: 1.5rem; }
        .arch-step-label { font-size: 0.72rem; color: #94a3b8; line-height: 1.4; white-space: pre-line; }
        .arch-note { font-size: 0.8rem; color: #64748b; margin: 0; }
        .arch-note strong { color: #00f3ff; }

        /* Agent template grid */
        .at-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.25rem; }

        /* Card */
        .at-card { position: relative; overflow: hidden; display: flex; flex-direction: column; gap: 0.85rem; }
        .at-accent { position: absolute; top: 0; left: 0; right: 0; height: 2px; }
        .at-head { display: flex; align-items: center; gap: 0.85rem; padding-top: 0.25rem; }
        .at-avatar {
          width: 48px; height: 48px; border-radius: 12px;
          display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        .at-icon { font-size: 1.6rem; }
        .at-identity { display: flex; flex-direction: column; gap: 0.2rem; }
        .at-role-badge {
          font-size: 0.6rem; font-weight: 700; font-family: 'Orbitron', monospace;
          text-transform: uppercase; letter-spacing: 0.08em;
          padding: 0.15rem 0.5rem; border-radius: 4px; border: 1px solid; width: fit-content;
        }
        .at-name { font-family: 'Orbitron', monospace; font-size: 1.1rem; font-weight: 700; margin: 0; color: #e2e8f0; }
        .at-desc { font-size: 0.83rem; color: #94a3b8; margin: 0; line-height: 1.5; }

        .at-section { display: flex; flex-direction: column; gap: 0.35rem; }
        .at-section-title { font-size: 0.65rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; }
        .at-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }
        .at-tag {
          font-size: 0.62rem; padding: 0.15rem 0.45rem;
          background: rgba(255,255,255,0.04); color: #94a3b8;
          border: 1px solid rgba(255,255,255,0.08); border-radius: 4px;
        }
        .at-tag--output {
          background: rgba(var(--agent-color-rgb, 0,243,255), 0.08);
          color: var(--agent-color, #00f3ff);
          border-color: rgba(var(--agent-color-rgb, 0,243,255), 0.2);
        }

        .at-rules { display: flex; flex-direction: column; gap: 0.5rem; }
        .at-rule { display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.5rem 0.6rem; border-radius: 7px; }
        .at-rule--auto  { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15); }
        .at-rule--block { background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.12); }
        .at-rule-icon { font-size: 0.9rem; flex-shrink: 0; margin-top: 1px; }
        .at-rule-label { display: block; font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; margin-bottom: 0.25rem; }
        .at-rule-items { display: flex; flex-wrap: wrap; gap: 0.25rem; }
        .at-rule-item {
          font-size: 0.6rem; padding: 0.1rem 0.35rem;
          background: rgba(16,185,129,0.08); color: #10b981;
          border: 1px solid rgba(16,185,129,0.18); border-radius: 3px;
        }
        .at-rule-item--warn { background: rgba(245,158,11,0.08); color: #f59e0b; border-color: rgba(245,158,11,0.18); }

        .at-result {
          padding: 0.5rem 0.7rem; border-radius: 6px; font-size: 0.78rem;
        }
        .at-result--ok  { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); color: #10b981; }
        .at-result--err { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.18); color: #fca5a5; }

        .at-spawn-btn {
          margin-top: auto;
          padding: 0.7rem 1rem;
          background: rgba(var(--btn-color-rgb, 0,243,255), 0.08);
          border: 1px solid var(--btn-color, #00f3ff);
          border-radius: 8px;
          color: var(--btn-color, #00f3ff);
          font-size: 0.75rem; font-weight: 700; font-family: 'Orbitron', monospace;
          text-transform: uppercase; letter-spacing: 0.08em;
          cursor: pointer; transition: all 0.2s;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        }
        .at-spawn-btn:hover:not(:disabled) {
          background: rgba(var(--btn-color-rgb, 0,243,255), 0.18);
          box-shadow: 0 0 20px rgba(var(--btn-color-rgb, 0,243,255), 0.25), inset 0 1px 0 rgba(255,255,255,0.08);
          transform: translateY(-1px);
        }
        .at-spawn-btn:disabled { opacity: 0.35; cursor: not-allowed; }

        .at-loading { text-align: center; padding: 4rem; color: #64748b; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
        .at-spinner {
          width: 44px; height: 44px; border: 3px solid rgba(139,92,246,0.12); border-top-color: #8b5cf6;
          border-radius: 50%; animation: at-spin 0.9s linear infinite;
        }
        @keyframes at-spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

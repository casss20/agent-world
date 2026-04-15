import React, { useEffect, useState, useCallback } from 'react';

const API = import.meta.env.VITE_API_URL || '';

// ── Channel metadata (mirrors backend CHANNEL_DEFINITIONS) ─────────────────
const CHANNEL_FIELDS = {
  etsy: [
    { key: 'api_key',      label: 'API Key',    type: 'password', help: 'From Etsy Developer portal → Your Apps' },
    { key: 'access_token', label: 'Access Token', type: 'password', help: 'OAuth access token for your Etsy shop' },
    { key: 'shop_id',      label: 'Shop ID',    type: 'text',     help: 'Your numeric Etsy shop ID' },
  ],
  shopify: [
    { key: 'store_domain',  label: 'Store Domain',  type: 'text',     help: 'e.g. your-store.myshopify.com' },
    { key: 'access_token',  label: 'Access Token',  type: 'password', help: 'Admin API access token from Shopify Partners' },
  ],
  gumroad: [
    { key: 'access_token',  label: 'Access Token',  type: 'password', help: 'From Gumroad → Settings → Advanced → Access Token' },
  ],
  amazon: [
    { key: 'refresh_token', label: 'Refresh Token', type: 'password', help: 'SP-API refresh token from Amazon developer console' },
    { key: 'client_id',     label: 'Client ID',     type: 'text',     help: 'LWA client ID' },
    { key: 'client_secret', label: 'Client Secret', type: 'password', help: 'LWA client secret' },
    { key: 'marketplace_id',label: 'Marketplace ID',type: 'text',     help: 'e.g. ATVPDKIKX0DER for US' },
  ],
  generic: [
    { key: 'endpoint_url',  label: 'Endpoint URL',  type: 'text',     help: 'https://your-api.com/webhook — receives JSON POSTs' },
    { key: 'api_key',       label: 'API Key',       type: 'password', help: 'Optional Authorization header value' },
  ],
};

const RISK_COLOR = { low: '#10b981', medium: '#f59e0b', high: '#ef4444' };

// ── Channel Card ───────────────────────────────────────────────────────────
function ChannelCard({ channel, onConnect, onDisconnect, onTest }) {
  const [open,    setOpen]    = useState(false);
  const [form,    setForm]    = useState({});
  const [loading, setLoading] = useState(false);
  const [testMsg, setTestMsg] = useState(null);

  const fields = CHANNEL_FIELDS[channel.id] || [];

  const handleConnect = async () => {
    setLoading(true);
    setTestMsg(null);
    const result = await onConnect(channel.id, form);
    setTestMsg(result);
    if (result?.ok) setOpen(false);
    setLoading(false);
  };

  const handleTest = async () => {
    setLoading(true);
    const result = await onTest(channel.id);
    setTestMsg(result);
    setLoading(false);
  };

  return (
    <div className={`channel-card glass-card ${channel.connected ? 'channel-card--connected' : ''}`}>
      {/* Header */}
      <div className="channel-header">
        <div className="channel-icon-wrap">
          <span className="channel-icon">{channel.icon}</span>
          {channel.connected && <span className="channel-badge channel-badge--live">LIVE</span>}
        </div>
        <div className="channel-meta">
          <h3 className="channel-name">{channel.name}</h3>
          <p className="channel-desc">{channel.description}</p>
          <div className="channel-tags">
            {channel.supported.map(s => (
              <span key={s} className="channel-tag">{s}</span>
            ))}
          </div>
        </div>
        <div className="channel-actions">
          {channel.connected ? (
            <>
              <button className="ch-btn ch-btn--test"    onClick={handleTest}                   disabled={loading}>Test</button>
              <button className="ch-btn ch-btn--danger"  onClick={() => onDisconnect(channel.id)} disabled={loading}>Disconnect</button>
            </>
          ) : (
            <button className="ch-btn ch-btn--connect" onClick={() => { setOpen(o => !o); setTestMsg(null); }}>
              {open ? 'Cancel' : 'Connect'}
            </button>
          )}
        </div>
      </div>

      {/* Connection status */}
      {testMsg && (
        <div className={`channel-status ${testMsg.ok ? 'channel-status--ok' : 'channel-status--err'}`}>
          {testMsg.ok ? '✓' : '✗'} {testMsg.message || (testMsg.ok ? 'Connected' : 'Failed')}
        </div>
      )}

      {/* Credentials form */}
      {open && !channel.connected && (
        <div className="channel-form">
          {fields.map(f => (
            <div key={f.key} className="ch-field">
              <label className="ch-label">{f.label}</label>
              <input
                id={`ch-${channel.id}-${f.key}`}
                type={f.type}
                placeholder={f.help}
                className="ch-input"
                value={form[f.key] || ''}
                onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                autoComplete="off"
              />
            </div>
          ))}
          <p className="ch-note">
            🔒 Credentials are stored locally on your machine only — never in source code or sent anywhere except the platform's own API.
          </p>
          <button className="ch-btn ch-btn--primary" onClick={handleConnect} disabled={loading}>
            {loading ? 'Connecting…' : `Connect ${channel.name}`}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Routing Summary ────────────────────────────────────────────────────────
function RoutingSummary({ routing }) {
  if (!routing) return null;
  return (
    <div className="routing-summary glass-cyan">
      <div className="routing-header">
        <span className="routing-title">🧭 Ledger Routing Status</span>
        <span className={`routing-badge ${routing.can_publish ? 'routing-badge--ok' : 'routing-badge--off'}`}>
          {routing.can_publish ? '⚡ Can Publish' : '⚠ No Live Channel'}
        </span>
      </div>
      <div className="routing-grid">
        {Object.entries(routing.approval_rules || {}).map(([type, rule]) => (
          <div key={type} className="routing-rule">
            <span className="routing-type">{type}</span>
            <span className="routing-rule-text">{rule}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────
export default function ChannelsPage() {
  const [channels, setChannels] = useState([]);
  const [routing,  setRouting]  = useState(null);
  const [loading,  setLoading]  = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [chRes, rtRes] = await Promise.all([
        fetch(`${API}/api/v1/channels`),
        fetch(`${API}/api/v1/channels/routing`),
      ]);
      if (chRes.ok) setChannels((await chRes.json()).channels || []);
      if (rtRes.ok) setRouting(await rtRes.json());
    } catch (e) {
      console.error('Channels fetch failed:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleConnect = async (channelId, config) => {
    try {
      const r = await fetch(`${API}/api/v1/channels/${channelId}/connect`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ config }),
      });
      const data = await r.json();
      if (data.ok) fetchData();
      return data;
    } catch (e) {
      return { ok: false, message: String(e) };
    }
  };

  const handleDisconnect = async (channelId) => {
    if (!confirm(`Disconnect ${channelId}? Saved credentials will be wiped.`)) return;
    await fetch(`${API}/api/v1/channels/${channelId}`, { method: 'DELETE' });
    fetchData();
  };

  const handleTest = async (channelId) => {
    try {
      const r = await fetch(`${API}/api/v1/channels/${channelId}/test`);
      return await r.json();
    } catch (e) {
      return { ok: false, message: String(e) };
    }
  };

  const connected = channels.filter(c => c.connected).length;

  return (
    <div className="channels-page">
      {/* ── Page Header ── */}
      <div className="channels-hero">
        <div className="channels-hero-inner">
          <div className="channels-hero-icon">🔌</div>
          <div>
            <h1 className="channels-title">Selling Channels</h1>
            <p className="channels-subtitle">
              Connect any platform. Agents stay platform-agnostic — the Ledger routes their outputs here.
            </p>
          </div>
          <div className="channels-stat">
            <span className="channels-stat-num">{connected}</span>
            <span className="channels-stat-lbl">Connected</span>
          </div>
        </div>
      </div>

      <div className="channels-body">
        {/* Routing summary */}
        <RoutingSummary routing={routing} />

        {/* Channel grid */}
        {loading ? (
          <div className="channels-loading">
            <div className="ch-spinner" />
            <p>Loading channels…</p>
          </div>
        ) : (
          <div className="channels-grid">
            {channels.map(ch => (
              <ChannelCard
                key={ch.id}
                channel={ch}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
                onTest={handleTest}
              />
            ))}
          </div>
        )}

        {/* How routing works */}
        <div className="routing-explainer glass">
          <h2 className="re-title">How the Ledger routes agent outputs</h2>
          <div className="re-steps">
            {[
              { n: '1', icon: '🤖', text: 'An agent (Nova, Forge, Pixel, Cipher, Ultron) produces a typed output' },
              { n: '2', icon: '🧭', text: 'The Ledger Router inspects the output type and evaluates risk' },
              { n: '3', icon: '🔔', text: 'High-risk outputs (listings, messages, assets) go to the approval queue' },
              { n: '4', icon: '✅', text: 'After human approval, the Router sends to the correct channel adapter here' },
              { n: '5', icon: '🚀', text: 'The adapter pushes to the actual platform (Shopify, Etsy, Gumroad…)' },
            ].map(s => (
              <div key={s.n} className="re-step">
                <span className="re-num">{s.n}</span>
                <span className="re-icon">{s.icon}</span>
                <span className="re-text">{s.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        .channels-page {
          min-height: 100vh;
          background:
            radial-gradient(ellipse 70% 50% at 15% 5%,  rgba(0,243,255,0.05)  0%, transparent 55%),
            radial-gradient(ellipse 50% 40% at 85% 90%, rgba(255,0,110,0.04) 0%, transparent 50%),
            #050a14;
          color: #e0e1dd;
          font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        }
        .channels-hero {
          border-bottom: 1px solid rgba(0,243,255,0.12);
          background: rgba(0,15,30,0.6);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          padding: 2.5rem 2rem;
        }
        .channels-hero-inner {
          max-width: 1100px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          gap: 1.5rem;
        }
        .channels-hero-icon { font-size: 3rem; filter: drop-shadow(0 0 16px #00f3ff); }
        .channels-title {
          font-family: 'Orbitron', monospace;
          font-size: 1.7rem;
          font-weight: 700;
          margin: 0 0 0.25rem;
          background: linear-gradient(135deg, #00f3ff, #7fb3d5);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .channels-subtitle { color: #64748b; margin: 0; font-size: 0.95rem; }
        .channels-stat { margin-left: auto; text-align: center; }
        .channels-stat-num {
          display: block; font-size: 2.2rem; font-weight: 700;
          font-family: 'Orbitron', monospace;
          color: #00f3ff; text-shadow: 0 0 12px rgba(0,243,255,0.5);
        }
        .channels-stat-lbl { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }

        .channels-body { max-width: 1100px; margin: 0 auto; padding: 2rem; display: flex; flex-direction: column; gap: 1.5rem; }

        /* Routing summary */
        .routing-summary {
          border-radius: 12px;
          padding: 1.25rem 1.5rem;
        }
        .routing-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
        .routing-title { font-family: 'Orbitron', monospace; font-size: 0.8rem; font-weight: 700; color: #00f3ff; text-transform: uppercase; letter-spacing: 0.1em; }
        .routing-badge {
          font-size: 0.72rem; font-weight: 700; font-family: 'Orbitron', monospace;
          padding: 0.3rem 0.75rem; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.08em;
        }
        .routing-badge--ok  { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.25); }
        .routing-badge--off { background: rgba(245,158,11,0.12);  color: #f59e0b; border: 1px solid rgba(245,158,11,0.25);  }
        .routing-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.6rem; }
        .routing-rule {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
          border-radius: 8px; padding: 0.6rem 0.75rem;
        }
        .routing-type { display: block; font-size: 0.68rem; font-weight: 700; color: #00f3ff; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.2rem; }
        .routing-rule-text { font-size: 0.75rem; color: #94a3b8; line-height: 1.4; }

        /* Channel cards */
        .channels-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
        @media (max-width: 768px) { .channels-grid { grid-template-columns: 1fr; } }

        .channel-card {
          transition: border-color 0.25s, box-shadow 0.25s;
        }
        .channel-card--connected {
          border-color: rgba(16,185,129,0.3) !important;
          box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(16,185,129,0.1) !important;
        }
        .channel-header { display: flex; align-items: flex-start; gap: 1rem; }
        .channel-icon-wrap { position: relative; }
        .channel-icon { font-size: 2.5rem; filter: drop-shadow(0 0 8px rgba(0,243,255,0.3)); }
        .channel-badge {
          position: absolute; top: -4px; right: -8px;
          font-size: 0.52rem; font-weight: 700; padding: 0.2rem 0.35rem; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.06em;
        }
        .channel-badge--live { background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid rgba(16,185,129,0.35); }
        .channel-meta { flex: 1; }
        .channel-name { font-family: 'Orbitron', monospace; font-size: 1rem; font-weight: 700; margin: 0 0 0.3rem; color: #e2e8f0; }
        .channel-desc { font-size: 0.82rem; color: #64748b; margin: 0 0 0.5rem; line-height: 1.4; }
        .channel-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }
        .channel-tag {
          font-size: 0.62rem; padding: 0.12rem 0.4rem;
          background: rgba(0,243,255,0.08); color: #00f3ff;
          border: 1px solid rgba(0,243,255,0.2); border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em;
        }
        .channel-actions { display: flex; flex-direction: column; gap: 0.4rem; flex-shrink: 0; }
        .ch-btn {
          font-size: 0.72rem; font-weight: 600; font-family: 'Orbitron', monospace;
          text-transform: uppercase; letter-spacing: 0.08em;
          padding: 0.45rem 1rem; border-radius: 6px; cursor: pointer;
          transition: all 0.2s; border: 1px solid transparent; white-space: nowrap;
        }
        .ch-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .ch-btn--connect { background: rgba(0,243,255,0.08); border-color: rgba(0,243,255,0.3); color: #00f3ff; }
        .ch-btn--connect:hover { background: rgba(0,243,255,0.18); box-shadow: 0 0 16px rgba(0,243,255,0.25); }
        .ch-btn--primary { background: rgba(0,243,255,0.12); border-color: #00f3ff; color: #00f3ff; width: 100%; padding: 0.6rem; margin-top: 0.5rem; }
        .ch-btn--primary:hover:not(:disabled) { background: rgba(0,243,255,0.25); box-shadow: 0 0 20px rgba(0,243,255,0.3); }
        .ch-btn--test   { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.15); color: #94a3b8; }
        .ch-btn--test:hover { background: rgba(255,255,255,0.1); color: #e2e8f0; }
        .ch-btn--danger { background: rgba(239,68,68,0.08); border-color: rgba(239,68,68,0.25); color: #fca5a5; }
        .ch-btn--danger:hover { background: rgba(239,68,68,0.18); }

        .channel-status {
          margin-top: 0.75rem; padding: 0.5rem 0.75rem; border-radius: 6px;
          font-size: 0.8rem; font-weight: 500;
        }
        .channel-status--ok  { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25); color: #10b981; }
        .channel-status--err { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);  color: #fca5a5; }

        .channel-form { margin-top: 1rem; display: flex; flex-direction: column; gap: 0.6rem; }
        .ch-field { display: flex; flex-direction: column; gap: 0.3rem; }
        .ch-label { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; }
        .ch-input {
          padding: 0.6rem 0.75rem;
          background: rgba(0,20,40,0.6); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
          border: 1px solid rgba(0,243,255,0.2); border-radius: 6px;
          color: #e0e1dd; font-size: 0.88rem; font-family: inherit; outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .ch-input:focus { border-color: #00f3ff; box-shadow: 0 0 0 2px rgba(0,243,255,0.1); }
        .ch-note { font-size: 0.75rem; color: #475569; margin: 0; line-height: 1.5; }

        /* Loading */
        .channels-loading { text-align: center; padding: 4rem; color: #64748b; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
        .ch-spinner {
          width: 44px; height: 44px; border: 3px solid rgba(0,243,255,0.12); border-top-color: #00f3ff;
          border-radius: 50%; animation: spin 0.9s linear infinite; box-shadow: 0 0 16px rgba(0,243,255,0.3);
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* How routing works */
        .routing-explainer { border-radius: 14px; padding: 1.5rem; }
        .re-title { font-family: 'Orbitron', monospace; font-size: 0.82rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 1rem; }
        .re-steps { display: flex; flex-direction: column; gap: 0.6rem; }
        .re-step {
          display: flex; align-items: center; gap: 0.75rem;
          padding: 0.6rem 0.75rem;
          background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
        }
        .re-num {
          width: 22px; height: 22px; background: rgba(0,243,255,0.1); border: 1px solid rgba(0,243,255,0.25);
          border-radius: 50%; display: flex; align-items: center; justify-content: center;
          font-size: 0.68rem; font-weight: 700; color: #00f3ff; font-family: 'Orbitron', monospace; flex-shrink: 0;
        }
        .re-icon { font-size: 1.1rem; flex-shrink: 0; }
        .re-text { font-size: 0.85rem; color: #94a3b8; line-height: 1.4; }
      `}</style>
    </div>
  );
}

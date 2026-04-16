import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

export function RevenueWidget({ businessId }) {
  const { get, loading } = useApi();
  const [data, setData] = useState(null);
  const [period, setPeriod] = useState('7d');
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    loadRevenue();
    loadAlerts();
  }, [businessId, period]);

  const loadRevenue = async () => {
    const result = await get(`/revenue/summary?business_id=${businessId}&period=${period}`);
    if (result) setData(result);
  };

  const loadAlerts = async () => {
    const result = await get(`/revenue/alerts?business_id=${businessId}`);
    if (result) setAlerts(result.alerts || []);
  };

  if (loading || !data) {
    return (
      <div className="bg-white/5 rounded-2xl border border-white/10 p-6 animate-pulse">
        <div className="h-8 bg-white/10 rounded w-1/3 mb-4"></div>
        <div className="grid grid-cols-4 gap-4">
          <div className="h-20 bg-white/10 rounded"></div>
          <div className="h-20 bg-white/10 rounded"></div>
          <div className="h-20 bg-white/10 rounded"></div>
          <div className="h-20 bg-white/10 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Period Selector */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Revenue & ROAS</h3>
          <p className="text-white/50 text-sm">Track sales, ad spend, and profitability</p>
        </div>
        <div className="flex gap-2">
          {['today', '7d', '30d'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              {p === 'today' ? 'Today' : p === '7d' ? '7 Days' : '30 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Revenue"
          value={`$${data.total_revenue?.toFixed(2) || '0.00'}`}
          trend={data.total_revenue > 0 ? '+active' : 'neutral'}
          icon="💰"
        />
        <MetricCard
          label="Ad Spend"
          value={`$${data.total_ad_spend?.toFixed(2) || '0.00'}`}
          trend={data.total_ad_spend > data.total_revenue ? 'negative' : 'neutral'}
          icon="📢"
        />
        <MetricCard
          label="ROAS"
          value={data.roas?.toFixed(2) || '0.00'}
          subtext={data.roas >= 2 ? 'Strong performance' : data.roas >= 1 ? 'Break-even' : 'Unprofitable'}
          trend={data.roas >= 1.5 ? 'positive' : data.roas >= 1 ? 'neutral' : 'negative'}
          icon="📊"
        />
        <MetricCard
          label="Net Profit"
          value={`$${data.net_profit?.toFixed(2) || '0.00'}`}
          trend={data.net_profit > 0 ? 'positive' : data.net_profit < 0 ? 'negative' : 'neutral'}
          icon="💵"
        />
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-white/70 flex items-center gap-2">
            ⚠️ Alerts ({alerts.length})
          </h4>
          <div className="space-y-2">
            {alerts.slice(0, 3).map((alert) => (
              <div
                key={alert.campaign_id}
                className={`p-3 rounded-xl border ${
                  alert.severity === 'critical'
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-yellow-500/10 border-yellow-500/30'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-medium text-white text-sm">{alert.campaign_name}</div>
                    <div className="text-xs text-white/50">ROAS: {alert.roas.toFixed(2)}</div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${
                    alert.severity === 'critical'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {alert.severity}
                  </span>
                </div>
                <p className="text-xs text-white/60 mt-2">{alert.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Channel Breakdown */}
      {Object.keys(data.by_channel || {}).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-white/70 mb-3">By Channel</h4>
          <div className="space-y-2">
            {Object.entries(data.by_channel).map(([channel, stats]) => (
              <div key={channel} className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                <div className="flex items-center gap-3">
                  <ChannelIcon channel={channel} />
                  <span className="text-white capitalize">{channel}</span>
                </div>
                <div className="text-right">
                  <div className="text-white font-medium">${stats.revenue?.toFixed(2)}</div>
                  <div className="text-xs text-white/50">{stats.orders} orders</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Campaign Performance */}
      {data.by_campaign?.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-white/70 mb-3">Top Campaigns</h4>
          <div className="space-y-2">
            {data.by_campaign.slice(0, 5).map((campaign) => (
              <div key={campaign.campaign_id} className="p-3 bg-white/5 rounded-xl">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium text-white text-sm">{campaign.campaign_name}</div>
                    <div className="text-xs text-white/50 capitalize">{campaign.platform}</div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${
                    campaign.roas >= 2
                      ? 'bg-green-500/20 text-green-400'
                      : campaign.roas >= 1
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}>
                    ROAS {campaign.roas?.toFixed(2)}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <div className="text-white/50">Spend</div>
                    <div className="text-white">${campaign.spend?.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-white/50">Revenue</div>
                    <div className="text-white">${campaign.revenue?.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-white/50">CPA</div>
                    <div className="text-white">${campaign.cpa?.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {(!data.by_campaign || data.by_campaign.length === 0) && 
       Object.keys(data.by_channel || {}).length === 0 && (
        <div className="text-center py-8 bg-white/5 rounded-2xl">
          <div className="text-4xl mb-2">📈</div>
          <p className="text-white/50">No revenue data yet</p>
          <p className="text-sm text-white/30 mt-1">
            Sales will appear here once Merchant agent makes sales
          </p>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, subtext, trend, icon }) {
  const trendColors = {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-white/60',
  };

  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
      <div className="flex items-center justify-between mb-2">
        <span className="text-white/50 text-sm">{label}</span>
        <span className="text-lg">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${trendColors[trend] || 'text-white'}`}>
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-white/40 mt-1">{subtext}</div>
      )}
    </div>
  );
}

function ChannelIcon({ channel }) {
  const icons = {
    etsy: '🛍️',
    amazon_kdp: '📚',
    shopify: '🛒',
    gumroad: '💎',
    stripe: '💳',
  };
  return <span className="text-lg">{icons[channel] || '📦'}</span>;
}

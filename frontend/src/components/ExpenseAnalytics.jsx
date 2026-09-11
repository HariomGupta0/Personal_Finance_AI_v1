import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieIcon, Layers, AlertCircle } from 'lucide-react';

const COLORS = [
  '#6366f1', // Indigo (Housing)
  '#06b6d4', // Cyan (Food)
  '#10b981', // Emerald (Transport)
  '#f59e0b', // Amber (Utilities)
  '#ec4899', // Pink (Shopping)
  '#8b5cf6', // Purple (Entertainment)
  '#3b82f6', // Blue (Healthcare)
  '#64748b'  // Slate (Misc)
];

export default function ExpenseAnalytics({ expenses }) {
  const sym = "₹";
  const categories = expenses?.categories || [
    { category: "Housing", amount: 12000, percentage: 57.14 },
    { category: "Food", amount: 4000, percentage: 19.05 },
    { category: "Utilities", amount: 3000, percentage: 14.29 },
    { category: "Transport", amount: 2000, percentage: 9.52 }
  ];

  const total = expenses?.total_expenses ?? 0;

  const chartData = categories.map(c => ({
    name: c.category,
    value: c.amount
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const percent = total > 0 ? ((data.value / total) * 100).toFixed(1) : 0;
      return (
        <div style={{
          background: 'rgba(17, 24, 39, 0.95)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '8px',
          padding: '8px 12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}>
          <div style={{ fontWeight: '600', color: 'var(--text-main)', fontSize: '0.85rem' }}>{data.name}</div>
          <div style={{ color: 'var(--accent-secondary)', fontSize: '0.8rem' }}>{sym}{data.value.toLocaleString()} ({percent}%)</div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-card" style={{ height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '8px', background: 'rgba(99, 102, 241, 0.15)', borderRadius: '8px', color: 'var(--accent-primary)' }}>
            <PieIcon size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Monthly Spending Breakdown</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Categorical expense distribution</p>
          </div>
        </div>
        <span className="badge badge-info">Total: {sym}{total.toLocaleString()}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 1fr) 1.2fr', gap: '20px', alignItems: 'center' }}>
        <div style={{ height: '220px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={85}
                paddingAngle={4}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {categories.map((cat, idx) => (
            <div key={idx}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)', fontWeight: '500' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: COLORS[idx % COLORS.length] }}></span>
                  {cat.category}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {sym}{cat.amount.toLocaleString()} <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>({cat.percentage}%)</span>
                </span>
              </div>
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '999px', overflow: 'hidden' }}>
                <div style={{
                  width: `${cat.percentage}%`,
                  height: '100%',
                  background: COLORS[idx % COLORS.length],
                  borderRadius: '999px'
                }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

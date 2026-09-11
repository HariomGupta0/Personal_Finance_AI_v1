import React from 'react';
import { Target, ShieldCheck, AlertTriangle, Landmark } from 'lucide-react';

export default function GoalManager({ summary, debt, emergency }) {
  const sym = "₹";

  const emergencyGoal = summary?.goals?.find((goal) => goal.name === 'Emergency Fund');
  const targetAmount = emergencyGoal?.target ?? 0;
  const currentAmount = emergencyGoal?.current ?? 0;
  const progressPercent = Math.min(100, Math.round((currentAmount / targetAmount) * 100));
  const shortfall = summary?.emergency_fund_shortfall ?? 0;
  const primaryLoan = debt?.loans?.[0];

  return (
    <div className="glass-card" style={{ height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '8px', background: 'rgba(6, 182, 212, 0.15)', borderRadius: '8px', color: 'var(--accent-secondary)' }}>
            <Target size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Savings Goals & Liabilities</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Emergency fund & active loans</p>
          </div>
        </div>
        <span className="badge badge-success">Target: {sym}{targetAmount.toLocaleString()}</span>
      </div>

      {/* Goal Progress */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem', marginBottom: '8px' }}>
          <span style={{ color: 'var(--text-main)', fontWeight: '600' }}>Emergency Fund Milestone</span>
          <span style={{ color: 'var(--accent-secondary)', fontWeight: '700' }}>{progressPercent}% Complete</span>
        </div>

        <div style={{ height: '10px', background: 'rgba(255,255,255,0.06)', borderRadius: '999px', overflow: 'hidden', marginBottom: '10px' }}>
          <div style={{
            width: `${progressPercent}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #6366f1, #06b6d4)',
            borderRadius: '999px'
          }}></div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-dim)' }}>
          <span>Current: {sym}{currentAmount.toLocaleString()}</span>
          <span>Buffer Shortfall: <strong style={{ color: '#f87171' }}>{sym}{shortfall.toLocaleString()}</strong></span>
        </div>
      </div>

      {/* Loan & Debt Snapshot */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '12px',
        padding: '14px',
        border: '1px solid var(--border-subtle)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)', fontWeight: '600', fontSize: '0.88rem' }}>
            <Landmark size={16} color="var(--accent-purple)" />
            {primaryLoan?.loan || 'No active loan'}
          </div>
          <span className={`badge ${primaryLoan ? 'badge-warning' : 'badge-success'}`}>{primaryLoan ? 'EMI Pending' : 'No EMI'}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          <div>
            <div>Outstanding Principal:</div>
            <div style={{ color: 'var(--text-main)', fontWeight: '600', fontSize: '0.95rem' }}>{sym}{(debt?.total_outstanding_debt ?? 0).toLocaleString()}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div>Upcoming Monthly EMI:</div>
            <div style={{ color: 'var(--accent-warning)', fontWeight: '600', fontSize: '0.95rem' }}>{sym}{(debt?.monthly_emi ?? 0).toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

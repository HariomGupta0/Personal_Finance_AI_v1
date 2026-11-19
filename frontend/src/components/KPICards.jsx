import React from 'react';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  PiggyBank,
  ShieldCheck,
  ShieldAlert,
  Activity,
  CreditCard,
  Landmark,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2
} from 'lucide-react';

const sym = "₹";
const fmt = (n) => (parseFloat(n) || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });

function CircularHealthGauge({ score, grade }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  const radius = 33;
  const circumference = 2 * Math.PI * radius; // ~207.35
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;

  // Grade color theme
  let startColor = '#10b981';
  let endColor = '#34d399';
  if (safeScore < 50 || grade === 'D' || grade === 'F') {
    startColor = '#ef4444';
    endColor = '#f87171';
  } else if (safeScore < 65 || grade === 'C') {
    startColor = '#f59e0b';
    endColor = '#fbbf24';
  } else if (safeScore < 80 || grade === 'B') {
    startColor = '#6366f1';
    endColor = '#06b6d4';
  }

  return (
    <div className="kpi-gauge-wrap">
      <svg width="84" height="84" viewBox="0 0 84 84" style={{ transform: 'rotate(-90deg)' }}>
        <defs>
          <linearGradient id="healthGaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={startColor} />
            <stop offset="100%" stopColor={endColor} />
          </linearGradient>
        </defs>
        {/* Background Track */}
        <circle
          cx="42"
          cy="42"
          r={radius}
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth="7"
          fill="transparent"
        />
        {/* Animated Progress Ring */}
        <circle
          cx="42"
          cy="42"
          r={radius}
          stroke="url(#healthGaugeGrad)"
          strokeWidth="7"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        />
      </svg>
      {/* Centered Score Label */}
      <div style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none'
      }}>
        <span style={{ fontSize: '1.28rem', fontWeight: '800', color: '#ffffff', lineHeight: 1 }}>
          {safeScore}
        </span>
        <span style={{ fontSize: '0.62rem', fontWeight: '600', color: 'var(--text-dim)', marginTop: 2 }}>
          /100
        </span>
      </div>
    </div>
  );
}

export default function KPICards({ summary, health, runway, debt }) {
  const totalBalance = (summary?.accounts || []).reduce((acc, curr) => acc + (curr.balance || 0), 0);
  const accountCount = summary?.accounts?.length || 0;
  const income = summary?.income ?? 0;
  const expenses = summary?.expenses ?? 0;
  const savings = summary?.savings ?? (income - expenses);
  const savingsRate = summary?.savings_rate ?? (income > 0 ? Math.round((savings / income) * 100) : 0);
  const healthScore = summary?.health_score ?? 0;
  const healthGrade = summary?.health_grade || (healthScore >= 80 ? 'A' : healthScore >= 65 ? 'B' : healthScore >= 50 ? 'C' : 'D');

  // Cashflow ratio calculation for segmented dual-tone bar
  const totalFlow = income > 0 ? income : (expenses > 0 ? expenses : 1);
  const spentPercent = Math.min(100, Math.max(0, Math.round((expenses / totalFlow) * 100)));
  const savedPercent = Math.max(0, 100 - spentPercent);

  // Health Standing text
  const healthStatusText = healthScore >= 80
    ? 'Optimal Standing'
    : healthScore >= 65
    ? 'Stable Standing'
    : healthScore >= 50
    ? 'Needs Attention'
    : 'High Risk';

  const healthBadgeStyle = healthScore >= 80
    ? 'badge-success'
    : healthScore >= 65
    ? 'badge-info'
    : healthScore >= 50
    ? 'badge-warning'
    : 'badge-danger';

  return (
    <div style={{ marginBottom: '28px' }}>
      {/* ── TOP HERO ROW (3 Primary Executive Cards) ── */}
      <div className="kpi-hero-grid">
        {/* 1. Total Liquid Balance Hero */}
        <div className="kpi-hero-card" style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(15, 23, 42, 0.75) 100%)',
          borderColor: 'rgba(99, 102, 241, 0.25)'
        }}>
          <div>
            <div className="kpi-hero-card-header">
              <div className="kpi-hero-icon-title">
                <div className="kpi-hero-icon-box" style={{ background: 'rgba(99, 102, 241, 0.18)', color: '#818cf8' }}>
                  <Wallet size={19} />
                </div>
                <span className="kpi-hero-title">Total Liquid Balance</span>
              </div>
              <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                {accountCount > 1 ? `${accountCount} Linked Banks` : 'Active Ledger'}
              </span>
            </div>

            <div className="kpi-hero-value-lg">
              {sym}{fmt(totalBalance)}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14, paddingTop: 12, borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '65%' }}>
              {accountCount > 0
                ? summary?.accounts?.map(a => a.bank).filter(Boolean).join(' • ') || 'Verified in Neo4j'
                : 'No bank linked'}
            </span>
            <span style={{
              fontSize: '0.72rem',
              fontWeight: '600',
              color: savings >= 0 ? '#34d399' : '#f87171',
              display: 'flex',
              alignItems: 'center',
              gap: 2
            }}>
              {savings >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              {savings >= 0 ? `+${sym}${fmt(savings)} net` : `-${sym}${fmt(Math.abs(savings))}`}
            </span>
          </div>
        </div>

        {/* 2. Monthly Cashflow Dynamics Hero */}
        <div className="kpi-hero-card" style={{
          background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.07) 0%, rgba(15, 23, 42, 0.75) 100%)',
          borderColor: 'rgba(6, 182, 212, 0.22)'
        }}>
          <div>
            <div className="kpi-hero-card-header">
              <div className="kpi-hero-icon-title">
                <div className="kpi-hero-icon-box" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#38bdf8' }}>
                  <TrendingUp size={19} />
                </div>
                <span className="kpi-hero-title">Monthly Cash Flow</span>
              </div>
              <span className={`badge ${savingsRate >= 20 ? 'badge-success' : savingsRate >= 0 ? 'badge-warning' : 'badge-danger'}`} style={{ fontSize: '0.7rem' }}>
                {savingsRate < 0 ? `${Math.abs(savingsRate)}% Deficit` : `${savingsRate}% Saved`}
              </span>
            </div>

            <div className="kpi-cashflow-split">
              <div className="kpi-cashflow-item">
                <span className="kpi-cashflow-label">
                  <ArrowUpRight size={12} color="#34d399" /> Inflow
                </span>
                <span className="kpi-cashflow-num" style={{ color: '#34d399' }}>
                  {sym}{fmt(income)}
                </span>
              </div>
              <div className="kpi-cashflow-item" style={{ textAlign: 'right' }}>
                <span className="kpi-cashflow-label" style={{ justifyContent: 'flex-end' }}>
                  <ArrowDownRight size={12} color="#f87171" /> Outflow
                </span>
                <span className="kpi-cashflow-num" style={{ color: '#f87171' }}>
                  {sym}{fmt(expenses)}
                </span>
              </div>
            </div>

            {/* Split Dual-Tone Cashflow Progress Bar */}
            <div className="kpi-cashflow-progress-track">
              <div className="kpi-cashflow-bar-spent" style={{ width: `${spentPercent}%` }} title={`Spent: ${spentPercent}%`} />
              <div className="kpi-cashflow-bar-saved" style={{ width: `${savedPercent}%` }} title={`Retained: ${savedPercent}%`} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.75rem' }}>
            <span style={{ color: savings < 0 ? '#f87171' : 'var(--text-dim)', fontWeight: savings < 0 ? '600' : 'normal' }}>
              {savings < 0 ? `Burn: ${Math.round((expenses / (income || 1)) * 100)}% of income` : 'Top Category:'}
            </span>
            <span style={{ color: 'var(--text-main)', fontWeight: '600' }}>
              {summary?.top_expense_category ? `Top: ${summary.top_expense_category}` : 'General'}
            </span>
          </div>
        </div>

        {/* 3. Financial Health Score Hero with Circular Radial Gauge */}
        <div className="kpi-hero-card" style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(15, 23, 42, 0.75) 100%)',
          borderColor: healthScore >= 80 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(99, 102, 241, 0.25)'
        }}>
          <div className="kpi-health-layout">
            <div className="kpi-health-info">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <Activity size={16} color="var(--accent-primary)" />
                <span className="kpi-hero-title">Financial Health</span>
              </div>
              <div>
                <span className={`badge ${healthBadgeStyle}`} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                  Grade {healthGrade} • {healthStatusText}
                </span>
              </div>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-dim)', lineHeight: 1.4, marginTop: 4, marginBottom: 0 }}>
                {healthScore >= 80
                  ? 'Runway, DTI & cash buffer are in safe balance.'
                  : healthScore >= 60
                  ? 'Stable standing. Consider accelerating emergency savings.'
                  : 'Action needed on debt EMI or runway buffer.'}
              </p>
            </div>

            {/* Circular Gauge */}
            <CircularHealthGauge score={healthScore} grade={healthGrade} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.74rem', color: 'var(--text-dim)' }}>
            <span>Verified Knowledge Graph Engine</span>
            <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: 4, fontWeight: '600' }}>
              <CheckCircle2 size={12} /> Active
            </span>
          </div>
        </div>
      </div>

      {/* ── SECONDARY HEALTH INDICATORS (Compact Row of 4 Pills) ── */}
      <div className="kpi-pills-grid">
        {/* Pill 1: Savings Rate */}
        <div className="kpi-pill-card">
          <div className="kpi-pill-left">
            <div className="kpi-pill-icon-box" style={{ background: 'rgba(99, 102, 241, 0.14)', color: '#818cf8' }}>
              <PiggyBank size={16} />
            </div>
            <div>
              <div className="kpi-pill-title">Savings Rate</div>
              <div className="kpi-pill-value">{savingsRate}%</div>
            </div>
          </div>
          <span className={`kpi-pill-badge ${savingsRate >= 20 ? 'badge-success' : savingsRate >= 0 ? 'badge-warning' : 'badge-danger'}`}>
            {savingsRate >= 20 ? 'Optimal (>20%)' : savingsRate >= 0 ? 'Below 20%' : 'Deficit'}
          </span>
        </div>

        {/* Pill 2: Emergency Runway */}
        <div className="kpi-pill-card">
          <div className="kpi-pill-left">
            <div className="kpi-pill-icon-box" style={{
              background: (runway?.runway_months ?? 0) >= 3 ? 'rgba(16, 185, 129, 0.14)' : 'rgba(245, 158, 11, 0.14)',
              color: (runway?.runway_months ?? 0) >= 3 ? '#34d399' : '#fbbf24'
            }}>
              {(runway?.runway_months ?? 0) >= 3 ? <ShieldCheck size={16} /> : <ShieldAlert size={16} />}
            </div>
            <div>
              <div className="kpi-pill-title">Emergency Runway</div>
              <div className="kpi-pill-value">{runway?.runway_months ?? 0} mo</div>
            </div>
          </div>
          <span className={`kpi-pill-badge ${(runway?.runway_months ?? 0) >= 3 ? 'badge-success' : 'badge-warning'}`}>
            {runway?.status || 'RUNWAY'}
          </span>
        </div>

        {/* Pill 3: Debt-to-Income (DTI) */}
        <div className="kpi-pill-card">
          <div className="kpi-pill-left">
            <div className="kpi-pill-icon-box" style={{ background: 'rgba(168, 85, 247, 0.14)', color: '#c084fc' }}>
              <CreditCard size={16} />
            </div>
            <div>
              <div className="kpi-pill-title">Debt-to-Income</div>
              <div className="kpi-pill-value">{summary?.dti_ratio ?? 0}%</div>
            </div>
          </div>
          <span className={`kpi-pill-badge ${(summary?.dti_ratio ?? 0) <= 20 ? 'badge-success' : 'badge-danger'}`}>
            {(summary?.dti_ratio ?? 0) <= 20 ? 'Healthy' : 'High Debt'}
          </span>
        </div>

        {/* Pill 4: Outstanding Debt & EMI */}
        <div className="kpi-pill-card">
          <div className="kpi-pill-left">
            <div className="kpi-pill-icon-box" style={{ background: 'rgba(6, 182, 212, 0.14)', color: '#38bdf8' }}>
              <Landmark size={16} />
            </div>
            <div>
              <div className="kpi-pill-title">Upcoming EMI</div>
              <div className="kpi-pill-value">{sym}{fmt(debt?.monthly_emi ?? 0)}<span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '400' }}>/mo</span></div>
            </div>
          </div>
          <span className="badge badge-info" style={{ fontSize: '0.68rem' }}>
            Debt: {sym}{fmt(debt?.total_outstanding_debt ?? 0)}
          </span>
        </div>
      </div>
    </div>
  );
}

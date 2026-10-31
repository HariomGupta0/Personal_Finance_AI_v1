import React, { useState } from 'react';
import {
  Sparkles,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Target,
  Clock,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  Calendar,
  Layers,
  Zap,
  Info,
  ArrowRight,
  PiggyBank,
  CreditCard,
  Sliders,
  Award,
  Edit3,
  Plus,
  Trash2,
  X,
  Check
} from 'lucide-react';

const sym = '₹';
const fmt = (n) => parseFloat(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });

const GOAL_PRESETS = [
  'Emergency Fund',
  'Home Down Payment',
  'Vehicle Purchase',
  'Vacation / Travel',
  'Tech / Gadget',
  'Higher Education'
];

export default function FinancialPlan({ plan, loading, onRefresh, onOpenImport, onDataChange }) {
  const [activeBudgetFilter, setActiveBudgetFilter] = useState('all'); // 'all' | 'needs' | 'wants'
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [goalFormData, setGoalFormData] = useState({
    name: '',
    target_amount: '',
    current_amount: '',
    target_date: '',
    isNew: false
  });
  const [isSavingGoal, setIsSavingGoal] = useState(false);
  const [goalError, setGoalError] = useState('');
  const [goalNotification, setGoalNotification] = useState('');

  if (loading && !plan) {
    return (
      <div className="glass-card" style={{ marginTop: '28px', padding: '40px 24px', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '56px', height: '56px', borderRadius: '16px', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent-primary)', marginBottom: '16px' }}>
          <Sparkles size={28} className="glow-pulse" />
        </div>
        <h3 style={{ fontSize: '1.25rem', marginBottom: '8px', color: 'var(--text-main)' }}>
          Generating Your Personalized Financial Plan...
        </h3>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', maxWidth: '520px', margin: '0 auto' }}>
          Analyzing transaction statements, computing discretionary spending caps, auditing recurring commitments, and calculating your emergency fund runway.
        </p>
      </div>
    );
  }

  if (!plan) return null;

  const {
    financial_summary = {},
    executive_summary = '',
    spending_insights = [],
    budget_plan = {},
    savings_plan = {},
    debt_and_commitments = {},
    prioritized_actions = [],
    data_limitations = [],
    reporting_month = '',
    ai_metadata = {}
  } = plan;

  const categories = budget_plan.categories || [];
  const filteredCategories = categories.filter(c => {
    if (activeBudgetFilter === 'needs') return !c.is_discretionary;
    if (activeBudgetFilter === 'wants') return c.is_discretionary;
    return true;
  });

  const isIncomeMissing = (financial_summary.monthly_income || 0) <= 0;

  const rawGoals = plan.goals || savings_plan.goals || [];
  const userGoals = rawGoals.length > 0 ? rawGoals : [
    {
      name: 'Emergency Fund',
      target: savings_plan.emergency_fund_3mo_target || 100000,
      current: savings_plan.emergency_fund_current || 30000,
      target_date: '2027-03-01'
    }
  ];

  const openEditGoalModal = (goalToEdit) => {
    setGoalError('');
    if (goalToEdit) {
      setGoalFormData({
        name: goalToEdit.name || 'Emergency Fund',
        target_amount: (goalToEdit.target ?? goalToEdit.target_amount ?? '').toString(),
        current_amount: (goalToEdit.current ?? goalToEdit.current_amount ?? 0).toString(),
        target_date: goalToEdit.target_date ? String(goalToEdit.target_date).slice(0, 10) : '',
        isNew: false
      });
    } else {
      const nextYear = new Date();
      nextYear.setFullYear(nextYear.getFullYear() + 1);
      const defaultDate = nextYear.toISOString().slice(0, 10);
      setGoalFormData({
        name: '',
        target_amount: '',
        current_amount: '0',
        target_date: defaultDate,
        isNew: true
      });
    }
    setIsGoalModalOpen(true);
  };

  const handleSaveGoal = async (e) => {
    if (e) e.preventDefault();
    if (!goalFormData.name?.trim()) {
      setGoalError('Please enter a goal name');
      return;
    }
    const targetNum = parseFloat(goalFormData.target_amount);
    if (isNaN(targetNum) || targetNum <= 0) {
      setGoalError('Please enter a target amount greater than ₹0');
      return;
    }
    const currentNum = parseFloat(goalFormData.current_amount || 0);

    setIsSavingGoal(true);
    setGoalError('');
    try {
      const res = await fetch('/api/goals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: goalFormData.name.trim(),
          target_amount: targetNum,
          current_amount: isNaN(currentNum) ? 0 : currentNum,
          target_date: goalFormData.target_date || undefined
        })
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to save goal');
      }
      setIsGoalModalOpen(false);
      setGoalNotification(`Goal "${goalFormData.name}" updated successfully! Plan recalculating...`);
      setTimeout(() => setGoalNotification(''), 4500);

      if (onRefresh) await onRefresh();
      if (onDataChange) await onDataChange();
    } catch (err) {
      setGoalError(err.message || 'Error saving goal');
    } finally {
      setIsSavingGoal(false);
    }
  };

  const handleDeleteGoal = async (goalName) => {
    if (!window.confirm(`Are you sure you want to delete the goal "${goalName}"?`)) return;
    setIsSavingGoal(true);
    setGoalError('');
    try {
      const res = await fetch(`/api/goals/${encodeURIComponent(goalName)}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to delete goal');
      }
      setIsGoalModalOpen(false);
      setGoalNotification(`Goal "${goalName}" removed.`);
      setTimeout(() => setGoalNotification(''), 4000);

      if (onRefresh) await onRefresh();
      if (onDataChange) await onDataChange();
    } catch (err) {
      setGoalError(err.message || 'Error deleting goal');
    } finally {
      setIsSavingGoal(false);
    }
  };

  return (
    <section style={{ marginTop: '36px' }} aria-label="Personalized Financial Plan">
      {/* Toast Notification */}
      {goalNotification && (
        <div className="animate-fade-in" style={{
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.4)',
          color: '#34d399',
          borderRadius: '12px',
          padding: '12px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.86rem',
          fontWeight: '600',
          boxShadow: '0 4px 15px rgba(16, 185, 129, 0.2)'
        }}>
          <CheckCircle2 size={18} />
          <span>{goalNotification}</span>
        </div>
      )}

      {/* Section Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        marginBottom: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(6, 182, 212, 0.2))',
            border: '1px solid var(--border-glow)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-glow)'
          }}>
            <Sparkles size={22} color="var(--accent-primary)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.35rem', fontWeight: '800', letterSpacing: '-0.02em', color: 'var(--text-main)' }}>
                Your Personalized Financial Plan
              </h2>
              <span className="badge" style={{
                background: ai_metadata.source === 'groq_llm' ? 'rgba(99, 102, 241, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                color: ai_metadata.source === 'groq_llm' ? '#818cf8' : '#34d399',
                border: `1px solid ${ai_metadata.source === 'groq_llm' ? 'rgba(99, 102, 241, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`
              }}>
                {ai_metadata.source === 'groq_llm' ? 'AI Grounded' : 'Engine Verified'}
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Data-driven financial blueprint for {reporting_month || 'Current Statement Period'} based on verified transactions
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="btn-secondary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.84rem' }}
          title="Regenerate plan using latest statement transactions"
        >
          <RefreshCw size={15} className={loading ? 'glow-pulse' : ''} />
          {loading ? 'Re-analyzing...' : 'Refresh Plan'}
        </button>
      </div>

      {/* Data Limitations Banner (if income is unrecorded or history short) */}
      {data_limitations.length > 0 && (
        <div style={{
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: '14px',
          padding: '14px 18px',
          marginBottom: '22px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px'
        }}>
          <AlertTriangle size={18} color="var(--accent-warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1, fontSize: '0.82rem', color: '#fbbf24', lineHeight: '1.5' }}>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>Data Observation & Limitation</div>
            {data_limitations.map((lim, idx) => (
              <p key={idx} style={{ margin: idx > 0 ? '4px 0 0 0' : 0 }}>{lim}</p>
            ))}
          </div>
          {onOpenImport && (
            <button
              onClick={onOpenImport}
              className="btn-secondary"
              style={{
                fontSize: '0.75rem',
                padding: '6px 12px',
                whiteSpace: 'nowrap',
                background: 'rgba(245, 158, 11, 0.15)',
                borderColor: 'rgba(245, 158, 11, 0.4)',
                color: '#fef3c7'
              }}
            >
              Upload More Statements
            </button>
          )}
        </div>
      )}

      {/* Main Grid: Executive Summary & Health Pulse */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '20px',
        marginBottom: '24px'
      }}>
        {/* Executive Summary Card */}
        <div className="glass-card" style={{ padding: '22px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent-primary)' }}>
              Executive Analysis
            </span>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.75rem',
              color: 'var(--text-muted)'
            }}>
              <ShieldCheck size={14} color="var(--accent-success)" /> 100% Grounded
            </span>
          </div>
          <p style={{
            fontSize: '0.94rem',
            color: 'var(--text-main)',
            lineHeight: '1.6',
            fontWeight: '400',
            marginBottom: '18px'
          }}>
            {executive_summary}
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '12px',
            paddingTop: '14px',
            borderTop: '1px solid var(--border-subtle)'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Observed Income</div>
              <div style={{ fontSize: '1rem', fontWeight: '700', color: isIncomeMissing ? 'var(--text-muted)' : '#34d399', marginTop: '2px' }}>
                {isIncomeMissing ? 'Unrecorded' : `${sym}${fmt(financial_summary.monthly_income)}`}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Monthly Outflow</div>
              <div style={{ fontSize: '1rem', fontWeight: '700', color: '#f87171', marginTop: '2px' }}>
                {sym}{fmt(financial_summary.monthly_expenses)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Net Savings Flow</div>
              <div style={{
                fontSize: '1rem',
                fontWeight: '700',
                color: (financial_summary.net_savings || 0) >= 0 ? '#34d399' : '#f87171',
                marginTop: '2px'
              }}>
                {(financial_summary.net_savings || 0) >= 0 ? '+' : ''}{sym}{fmt(financial_summary.net_savings)}
              </div>
            </div>
          </div>
        </div>

        {/* Financial Standing & Potential Savings */}
        <div className="glass-card" style={{ padding: '22px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent-secondary)' }}>
                Target Financial Health
              </span>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: financial_summary.health_grade === 'A' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(99, 102, 241, 0.2)',
                color: financial_summary.health_grade === 'A' ? '#34d399' : 'var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: '800',
                fontSize: '0.95rem'
              }}>
                {financial_summary.health_grade || 'C'}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--text-main)' }}>
                {financial_summary.health_score || 50}
              </span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ 100 Health Score</span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.45', marginBottom: '16px' }}>
              {financial_summary.health_assessment || 'Financial wellness based on current savings, reserve cushion, and debt commitments.'}
            </p>
          </div>

          <div style={{
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(16, 185, 129, 0.08))',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            borderRadius: '12px',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Zap size={13} color="var(--accent-success)" /> Monthly Savings Potential
              </div>
              <div style={{ fontSize: '1.15rem', fontWeight: '800', color: '#34d399', marginTop: '2px' }}>
                +{sym}{fmt(budget_plan.total_potential_savings)}
                <span style={{ fontSize: '0.75rem', fontWeight: '400', color: 'var(--text-muted)', marginLeft: '4px' }}>/mo</span>
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              From Budget
              <div style={{ fontWeight: '600', color: 'var(--text-main)', marginTop: '2px' }}>Optimization</div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Spending Insights Chips */}
      {spending_insights.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700', marginBottom: '12px', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--accent-primary)" /> Key Spending Observations
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {spending_insights.map((ins, idx) => (
              <div key={idx} className="glass-card" style={{ padding: '16px 18px', background: 'rgba(255, 255, 255, 0.02)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.74rem', fontWeight: '700', color: 'var(--accent-secondary)', textTransform: 'uppercase' }}>
                    {ins.topic || 'Insight'}
                  </span>
                  {ins.category && (
                    <span className="badge" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                      {ins.category}
                    </span>
                  )}
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: '1.45' }}>
                  {ins.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Two Column Grid: Recommended Monthly Budget & Savings Target Strategy */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
        gap: '20px',
        marginBottom: '28px'
      }}>
        {/* Recommended Monthly Budget */}
        <div className="glass-card" style={{ padding: '22px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={18} color="var(--accent-primary)" /> Suggested Monthly Budget
              </h3>
              <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Target caps protect essentials while trimming lifestyle outflow
              </p>
            </div>

            {/* Filter pills */}
            <div style={{ display: 'flex', gap: '4px', background: 'rgba(255, 255, 255, 0.04)', padding: '3px', borderRadius: '8px' }}>
              {['all', 'wants', 'needs'].map(f => (
                <button
                  key={f}
                  onClick={() => setActiveBudgetFilter(f)}
                  style={{
                    border: 'none',
                    background: activeBudgetFilter === f ? 'var(--accent-primary)' : 'transparent',
                    color: activeBudgetFilter === f ? '#fff' : 'var(--text-muted)',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {f === 'all' ? 'All' : f === 'wants' ? 'Wants' : 'Needs'}
                </button>
              ))}
            </div>
          </div>

          {/* Budget Categories List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '380px', overflowY: 'auto', paddingRight: '4px' }}>
            {filteredCategories.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                No categories match the selected filter.
              </div>
            ) : (
              filteredCategories.map((cat, i) => {
                const current = cat.current_spending || 0;
                const limit = cat.recommended_limit || current;
                const savings = cat.potential_savings || 0;
                const ratio = limit > 0 ? Math.min(100, Math.round((current / limit) * 100)) : 100;
                const isOver = savings > 0;

                return (
                  <div key={i} style={{
                    padding: '12px 14px',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '10px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: '600', fontSize: '0.88rem', color: 'var(--text-main)' }}>
                          {cat.category}
                        </span>
                        <span style={{
                          fontSize: '0.68rem',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background: cat.is_discretionary ? 'rgba(245, 158, 11, 0.12)' : 'rgba(99, 102, 241, 0.12)',
                          color: cat.is_discretionary ? '#fbbf24' : '#818cf8',
                          fontWeight: '600'
                        }}>
                          {cat.is_discretionary ? 'Discretionary' : 'Essential'}
                        </span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontWeight: '700', fontSize: '0.9rem', color: isOver ? '#fbbf24' : 'var(--text-main)' }}>
                          {sym}{fmt(current)}
                        </span>
                        <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginLeft: '4px' }}>
                          / {sym}{fmt(limit)} cap
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div style={{
                      width: '100%',
                      height: '6px',
                      background: 'rgba(255, 255, 255, 0.08)',
                      borderRadius: '999px',
                      overflow: 'hidden',
                      marginBottom: '6px'
                    }}>
                      <div style={{
                        width: `${Math.min(100, (current / (limit || 1)) * 100)}%`,
                        height: '100%',
                        background: isOver
                          ? 'linear-gradient(90deg, #fbbf24, #f87171)'
                          : 'linear-gradient(90deg, #06b6d4, #10b981)',
                        borderRadius: '999px',
                        transition: 'width 0.4s ease'
                      }} />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {cat.percentage_of_expenses?.toFixed(1)}% of total monthly spend
                      </span>
                      {savings > 0 ? (
                        <span style={{ color: '#34d399', fontWeight: '600' }}>
                          Save {sym}{fmt(savings)} by capping at limit
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>On Target</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Savings Strategy & Emergency Fund Timeline */}
        <div className="glass-card" style={{ padding: '22px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Target size={18} color="#34d399" /> Savings & Financial Goals
                </h3>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Customizable personal targets & 3-month statutory emergency buffer
                </p>
              </div>
              <button
                type="button"
                onClick={() => openEditGoalModal()}
                className="btn-secondary"
                style={{ fontSize: '0.75rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                title="Add or manually customize your savings goals"
              >
                <Sliders size={13} color="var(--accent-secondary)" />
                <span>Adjust Goals</span>
              </button>
            </div>

            {/* Target Breakdown Box */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>3-Month Emergency Benchmark</span>
                <span style={{ fontSize: '1.15rem', fontWeight: '800', color: 'var(--text-main)' }}>
                  {sym}{fmt(savings_plan.emergency_fund_3mo_target)}
                </span>
              </div>

              {/* Cushion vs Shortfall Bar */}
              <div style={{
                width: '100%',
                height: '8px',
                background: 'rgba(255, 255, 255, 0.08)',
                borderRadius: '999px',
                overflow: 'hidden',
                marginBottom: '10px'
              }}>
                <div style={{
                  width: `${Math.min(100, Math.round(((savings_plan.emergency_fund_current || 0) / (savings_plan.emergency_fund_3mo_target || 1)) * 100))}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #6366f1, #10b981)',
                  borderRadius: '999px'
                }} />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem' }}>
                <span style={{ color: '#34d399', fontWeight: '600' }}>
                  Current Reserve: {sym}{fmt(savings_plan.emergency_fund_current)}
                </span>
                <span style={{ color: (savings_plan.emergency_fund_shortfall || 0) > 0 ? '#fbbf24' : '#34d399', fontWeight: '600' }}>
                  Gap: {sym}{fmt(savings_plan.emergency_fund_shortfall)}
                </span>
              </div>
            </div>

            {/* Monthly Target Pace */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <PiggyBank size={13} color="var(--accent-primary)" /> Monthly Savings Target
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '700', color: '#34d399', marginTop: '4px' }}>
                  {sym}{fmt(savings_plan.recommended_monthly_savings)}
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>/mo</span>
                </div>
              </div>

              <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={13} color="var(--accent-secondary)" /> Estimated Timeline
                </div>
                <div style={{ fontSize: '0.92rem', fontWeight: '700', color: 'var(--text-main)', marginTop: '4px' }}>
                  {savings_plan.estimated_months_to_target !== null
                    ? `${savings_plan.estimated_months_to_target} Months`
                    : 'See Recommendation'}
                </div>
              </div>
            </div>

            {/* Tracked Goals Section */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '14px 16px',
              marginBottom: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.76rem', fontWeight: '700', color: 'var(--accent-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Active Financial Goals ({userGoals.length})
                </span>
                <button
                  type="button"
                  onClick={() => openEditGoalModal(null)}
                  style={{
                    background: 'rgba(99, 102, 241, 0.12)',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    color: '#818cf8',
                    borderRadius: '6px',
                    padding: '3px 8px',
                    fontSize: '0.72rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Plus size={12} /> Add Goal
                </button>
              </div>

              {/* In-place Goal Customization Editor (Occurs right at that place) */}
              {isGoalModalOpen && (
                <div className="animate-fade-in" style={{
                  background: 'rgba(17, 24, 39, 0.95)',
                  border: '1px solid var(--border-glow)',
                  borderRadius: '12px',
                  padding: '18px',
                  marginBottom: '14px',
                  boxShadow: '0 8px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(99, 102, 241, 0.2)'
                }}>
                  {/* Editor Header */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '8px',
                        background: 'rgba(99, 102, 241, 0.15)',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <Sliders size={14} color="var(--accent-primary)" />
                      </div>
                      <div>
                        <h4 style={{ fontSize: '0.98rem', color: 'var(--text-main)', fontWeight: '700' }}>
                          {goalFormData.isNew ? 'Create New Financial Goal' : `Edit Goal: ${goalFormData.name}`}
                        </h4>
                        <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          Customize target amounts, deadlines, and balance
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsGoalModalOpen(false)}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        padding: '4px',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>

                  {goalError && (
                    <div style={{
                      background: 'rgba(239, 68, 68, 0.12)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      color: '#f87171',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '0.76rem',
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <AlertTriangle size={14} />
                      <span>{goalError}</span>
                    </div>
                  )}

                  <form onSubmit={handleSaveGoal} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {/* Goal Name */}
                    <div>
                      <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '600' }}>
                        Goal Name
                      </label>
                      <input
                        type="text"
                        value={goalFormData.name}
                        onChange={(e) => setGoalFormData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g. Emergency Fund, New Vehicle, Vacation..."
                        disabled={!goalFormData.isNew && goalFormData.name.toLowerCase() === 'emergency fund'}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--text-main)',
                          fontSize: '0.86rem',
                          outline: 'none'
                        }}
                      />

                      {/* Goal Presets if new */}
                      {goalFormData.isNew && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                          {GOAL_PRESETS.map(preset => (
                            <button
                              type="button"
                              key={preset}
                              onClick={() => setGoalFormData(prev => ({ ...prev, name: preset }))}
                              style={{
                                background: goalFormData.name === preset ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255, 255, 255, 0.03)',
                                border: `1px solid ${goalFormData.name === preset ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                                color: goalFormData.name === preset ? '#a5b4fc' : 'var(--text-muted)',
                                borderRadius: '6px',
                                padding: '2px 7px',
                                fontSize: '0.68rem',
                                cursor: 'pointer'
                              }}
                            >
                              {preset}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Target Amount */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                        <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '600' }}>
                          Target Amount (₹)
                        </label>
                        {savings_plan.emergency_fund_3mo_target > 0 && goalFormData.name.toLowerCase() === 'emergency fund' && (
                          <button
                            type="button"
                            onClick={() => setGoalFormData(prev => ({ ...prev, target_amount: savings_plan.emergency_fund_3mo_target }))}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#34d399',
                              fontSize: '0.68rem',
                              cursor: 'pointer',
                              textDecoration: 'underline'
                            }}
                          >
                            Set to 3-Mo Benchmark (₹{fmt(savings_plan.emergency_fund_3mo_target)})
                          </button>
                        )}
                      </div>
                      <input
                        type="number"
                        step="1000"
                        min="1000"
                        value={goalFormData.target_amount}
                        onChange={(e) => setGoalFormData(prev => ({ ...prev, target_amount: e.target.value }))}
                        placeholder="e.g. 150000"
                        required
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--text-main)',
                          fontSize: '0.86rem',
                          outline: 'none'
                        }}
                      />

                      {/* Quick Increment Chips */}
                      <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                        {[10000, 25000, 50000, 100000].map(inc => (
                          <button
                            type="button"
                            key={inc}
                            onClick={() => setGoalFormData(prev => ({
                              ...prev,
                              target_amount: (parseFloat(prev.target_amount || 0) + inc).toString()
                            }))}
                            style={{
                              background: 'rgba(255, 255, 255, 0.04)',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--text-muted)',
                              borderRadius: '6px',
                              padding: '2px 7px',
                              fontSize: '0.68rem',
                              cursor: 'pointer'
                            }}
                          >
                            +₹{inc >= 100000 ? `${inc / 100000}L` : `${inc / 1000}k`}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Current Saved Amount */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                        <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '600' }}>
                          Current Saved Balance (₹)
                        </label>
                        {financial_summary.liquid_balance > 0 && (
                          <button
                            type="button"
                            onClick={() => setGoalFormData(prev => ({ ...prev, current_amount: financial_summary.liquid_balance }))}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#818cf8',
                              fontSize: '0.68rem',
                              cursor: 'pointer',
                              textDecoration: 'underline'
                            }}
                          >
                            Use Bank Balance (₹{fmt(financial_summary.liquid_balance)})
                          </button>
                        )}
                      </div>
                      <input
                        type="number"
                        step="1000"
                        min="0"
                        value={goalFormData.current_amount}
                        onChange={(e) => setGoalFormData(prev => ({ ...prev, current_amount: e.target.value }))}
                        placeholder="e.g. 30000"
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--text-main)',
                          fontSize: '0.86rem',
                          outline: 'none'
                        }}
                      />
                    </div>

                    {/* Target Completion Date */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                        <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '600' }}>
                          Target Milestone Date
                        </label>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          {[
                            { label: '+6M', months: 6 },
                            { label: '+1Y', months: 12 },
                            { label: '+2Y', months: 24 }
                          ].map(opt => (
                            <button
                              type="button"
                              key={opt.label}
                              onClick={() => {
                                const d = new Date();
                                d.setMonth(d.getMonth() + opt.months);
                                setGoalFormData(prev => ({ ...prev, target_date: d.toISOString().slice(0, 10) }));
                              }}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--accent-secondary)',
                                fontSize: '0.68rem',
                                cursor: 'pointer'
                              }}
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>
                      </div>
                      <input
                        type="date"
                        value={goalFormData.target_date}
                        onChange={(e) => setGoalFormData(prev => ({ ...prev, target_date: e.target.value }))}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--text-main)',
                          fontSize: '0.86rem',
                          outline: 'none'
                        }}
                      />
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px', gap: '8px' }}>
                      <div>
                        {!goalFormData.isNew && goalFormData.name.toLowerCase() !== 'emergency fund' && (
                          <button
                            type="button"
                            onClick={() => handleDeleteGoal(goalFormData.name)}
                            disabled={isSavingGoal}
                            style={{
                              background: 'rgba(239, 68, 68, 0.1)',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              color: '#f87171',
                              borderRadius: '8px',
                              padding: '7px 12px',
                              fontSize: '0.78rem',
                              fontWeight: '600',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}
                          >
                            <Trash2 size={13} /> Delete
                          </button>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          type="button"
                          onClick={() => setIsGoalModalOpen(false)}
                          className="btn-secondary"
                          style={{ padding: '7px 14px', fontSize: '0.8rem' }}
                          disabled={isSavingGoal}
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="btn-primary"
                          disabled={isSavingGoal}
                          style={{ padding: '7px 16px', fontSize: '0.8rem' }}
                        >
                          {isSavingGoal ? 'Saving...' : 'Save & Update Plan'}
                        </button>
                      </div>
                    </div>
                  </form>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {userGoals.map((g, idx) => {
                  const gTarget = parseFloat(g.target ?? g.target_amount ?? 0);
                  const gCurrent = parseFloat(g.current ?? g.current_amount ?? 0);
                  const pct = gTarget > 0 ? Math.min(100, Math.round((gCurrent / gTarget) * 100)) : 0;
                  const isEmergency = (g.name || '').toLowerCase() === 'emergency fund';

                  return (
                    <div key={g.id || g.name || idx} style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      borderRadius: '8px',
                      padding: '10px 12px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{
                            width: '22px',
                            height: '22px',
                            borderRadius: '6px',
                            background: isEmergency ? 'rgba(16, 185, 129, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                            color: isEmergency ? '#34d399' : '#818cf8',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            <Target size={12} />
                          </div>
                          <div>
                            <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-main)' }}>
                              {g.name}
                            </span>
                            {g.target_date && (
                              <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginLeft: '8px' }}>
                                Due: {String(g.target_date).slice(0, 10)}
                              </span>
                            )}
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-main)' }}>
                            {sym}{fmt(gCurrent)} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: '400' }}>/ {sym}{fmt(gTarget)}</span>
                          </span>
                          <button
                            type="button"
                            onClick={() => openEditGoalModal(g)}
                            title="Edit this goal"
                            style={{
                              background: 'rgba(255, 255, 255, 0.05)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: '5px',
                              padding: '3px 6px',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center'
                            }}
                          >
                            <Edit3 size={11} />
                          </button>
                          {!isEmergency && (
                            <button
                              type="button"
                              onClick={() => handleDeleteGoal(g.name)}
                              title="Delete this goal"
                              style={{
                                background: 'rgba(239, 68, 68, 0.08)',
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                borderRadius: '5px',
                                padding: '3px 6px',
                                color: '#f87171',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center'
                              }}
                            >
                              <Trash2 size={11} />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Mini progress bar */}
                      <div style={{
                        width: '100%',
                        height: '5px',
                        background: 'rgba(255, 255, 255, 0.06)',
                        borderRadius: '999px',
                        overflow: 'hidden',
                        marginBottom: '4px'
                      }}>
                        <div style={{
                          width: `${pct}%`,
                          height: '100%',
                          background: pct >= 100
                            ? '#10b981'
                            : 'linear-gradient(90deg, #6366f1, #06b6d4)',
                          borderRadius: '999px'
                        }} />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        <span>{pct}% Funded</span>
                        <span>{gTarget > gCurrent ? `Gap: ${sym}${fmt(gTarget - gCurrent)}` : 'Completed 🎉'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Fixed Commitments & EMIs footer */}
          <div style={{
            padding: '12px 14px',
            background: 'rgba(255, 255, 255, 0.02)',
            borderRadius: '10px',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CreditCard size={16} color="var(--accent-secondary)" />
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-main)' }}>
                  Active Commitments & EMIs
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {debt_and_commitments.recurring_commitments?.length || 0} recurring item(s) detected
                </div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.86rem', fontWeight: '700', color: '#fbbf24' }}>
                {sym}{fmt(debt_and_commitments.total_recurring_monthly)}/mo
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                DTI: {debt_and_commitments.dti_ratio?.toFixed(1) || 0}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Prioritized Action Recommendations (3 to 5 ranked actions) */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: '800', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Award size={20} color="var(--accent-primary)" /> Prioritized Action Steps
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Specific, practical actions ranked by immediate impact on your financial health
            </p>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Ranked by financial return & risk reduction
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {prioritized_actions.map((act, index) => {
            const isHigh = act.priority === 'HIGH';
            const isMedium = act.priority === 'MEDIUM';

            return (
              <div
                key={index}
                style={{
                  padding: '16px 18px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: isHigh ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  display: 'flex',
                  gap: '16px',
                  alignItems: 'flex-start',
                  transition: 'all 0.2s ease'
                }}
              >
                {/* Priority Number Badge */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: isHigh
                    ? 'rgba(239, 68, 68, 0.15)'
                    : isMedium
                      ? 'rgba(245, 158, 11, 0.15)'
                      : 'rgba(99, 102, 241, 0.15)',
                  color: isHigh ? '#f87171' : isMedium ? '#fbbf24' : '#818cf8',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: '800',
                  fontSize: '0.9rem',
                  flexShrink: 0
                }}>
                  {index + 1}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
                    <h4 style={{ fontSize: '0.94rem', fontWeight: '700', color: 'var(--text-main)' }}>
                      {act.title}
                    </h4>
                    <span style={{
                      fontSize: '0.68rem',
                      fontWeight: '700',
                      padding: '2px 8px',
                      borderRadius: '999px',
                      textTransform: 'uppercase',
                      background: isHigh ? 'rgba(239, 68, 68, 0.15)' : isMedium ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                      color: isHigh ? '#f87171' : isMedium ? '#fbbf24' : '#818cf8',
                      border: `1px solid ${isHigh ? 'rgba(239, 68, 68, 0.3)' : isMedium ? 'rgba(245, 158, 11, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`
                    }}>
                      {act.priority} PRIORITY
                    </span>
                    {act.category && (
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        · {act.category}
                      </span>
                    )}
                  </div>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', lineHeight: '1.5', marginBottom: '8px' }}>
                    {act.action}
                  </p>

                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    gap: '14px',
                    fontSize: '0.78rem',
                    paddingTop: '8px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.04)'
                  }}>
                    {act.expected_impact && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399', fontWeight: '600' }}>
                        <TrendingUp size={14} /> Expected Impact: {act.expected_impact}
                      </div>
                    )}
                    {act.rationale && (
                      <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Info size={13} /> Why: {act.rationale}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </section>
  );
}

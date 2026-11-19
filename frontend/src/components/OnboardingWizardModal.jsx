import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Shield,
  TrendingUp,
  AlertCircle,
  Building,
  DollarSign,
  Wallet,
  X
} from 'lucide-react';

const COMMON_BANKS = [
  { id: 'HDFC Bank', label: 'HDFC Bank', color: '#004c8f' },
  { id: 'State Bank of India', label: 'SBI', color: '#280071' },
  { id: 'ICICI Bank', label: 'ICICI Bank', color: '#f37e20' },
  { id: 'Axis Bank', label: 'Axis Bank', color: '#97144d' }
];

export default function OnboardingWizardModal({ isOpen, onClose, onComplete, onOpenConnectBank }) {
  if (!isOpen) return null;

  const [step, setStep] = useState(1);
  const [bankName, setBankName] = useState('HDFC Bank');
  const [monthlyIncome, setMonthlyIncome] = useState(75000);
  const [liquidBalance, setLiquidBalance] = useState(150000);
  const [monthlyEmi, setMonthlyEmi] = useState(15000);
  const [loanType, setLoanType] = useState('Personal Loan');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Live Deterministic Calculations
  const livingBurn = Math.max(15000, monthlyIncome * 0.5);
  const runwayMonths = livingBurn > 0 ? (liquidBalance / livingBurn).toFixed(1) : 0;
  const dtiRatio = monthlyIncome > 0 ? ((monthlyEmi / monthlyIncome) * 100).toFixed(1) : 0;
  
  // Deterministic health score formula
  const healthScore = Math.min(
    100,
    Math.max(
      0,
      Math.round((100 - dtiRatio) * 0.4 + Math.min(runwayMonths / 6.0, 1.0) * 40 + 20)
    )
  );

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      setError(null);
      const res = await fetch('/api/onboarding/bootstrap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bank_name: bankName,
          liquid_balance_inr: parseFloat(liquidBalance),
          monthly_income_inr: parseFloat(monthlyIncome),
          monthly_emi_inr: parseFloat(monthlyEmi),
          loan_type: monthlyEmi > 0 ? loanType : 'None'
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to bootstrap account');
      }

      const data = await res.json();
      if (onComplete) {
        onComplete(data);
      }
      onClose();
    } catch (err) {
      console.error('Bootstrap error:', err);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(5, 8, 15, 0.85)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-card animate-fade-in" style={{
        maxWidth: '780px',
        width: '100%',
        padding: '32px',
        borderRadius: '20px',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7), 0 0 30px rgba(99, 102, 241, 0.2)',
        position: 'relative'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px'
          }}
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Sparkles size={20} color="#ffffff" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: '800' }}>
              60-Second Financial Setup
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Zero cold-start. Calibrate your deterministic AI twin in 3 quick questions.
            </p>
          </div>
        </div>

        {/* Step Progress Bar */}
        <div style={{
          display: 'flex',
          gap: '8px',
          margin: '20px 0 24px 0'
        }}>
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              style={{
                flex: 1,
                height: '4px',
                borderRadius: '2px',
                background: s <= step ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.1)',
                transition: 'all 0.3s ease'
              }}
            />
          ))}
        </div>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            padding: '10px 14px',
            borderRadius: '8px',
            color: '#f87171',
            fontSize: '0.85rem',
            marginBottom: '16px'
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Main Grid: Form Inputs (Left) & Real-time Metrics Simulator (Right) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '24px', alignItems: 'start' }}>
          
          {/* Step Contents */}
          <div>
            {step === 1 && (
              <div className="animate-fade-in">
                <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', marginBottom: '12px' }}>
                  Question 1 of 3
                </span>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '6px' }}>What is your monthly net income?</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '18px' }}>
                  Your in-hand salary or recurring monthly earnings. Used to establish your baseline burn rate.
                </p>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
                    Monthly Income (₹)
                  </label>
                  <input
                    type="number"
                    value={monthlyIncome}
                    onChange={(e) => setMonthlyIncome(Math.max(0, Number(e.target.value)))}
                    className="form-input"
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      fontSize: '1.1rem',
                      fontWeight: '700',
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      color: '#ffffff'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {[35000, 50000, 75000, 120000, 200000].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setMonthlyIncome(val)}
                      style={{
                        padding: '6px 12px',
                        background: monthlyIncome === val ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        fontSize: '0.78rem',
                        cursor: 'pointer'
                      }}
                    >
                      ₹{(val / 1000).toFixed(0)}k
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="animate-fade-in">
                <span className="badge" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee', marginBottom: '12px' }}>
                  Question 2 of 3
                </span>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '6px' }}>How much do you currently have in bank savings?</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '18px' }}>
                  Total liquid cash across your savings accounts. This forms your emergency runway shield.
                </p>

                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
                    Primary Bank
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginBottom: '12px' }}>
                    {COMMON_BANKS.map((b) => (
                      <button
                        key={b.id}
                        type="button"
                        onClick={() => setBankName(b.id)}
                        style={{
                          padding: '8px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          background: bankName === b.id ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                          border: `1px solid ${bankName === b.id ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                          borderRadius: '8px',
                          color: '#ffffff',
                          fontSize: '0.82rem',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: b.color }} />
                        <span>{b.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
                    Total Liquid Balance (₹)
                  </label>
                  <input
                    type="number"
                    value={liquidBalance}
                    onChange={(e) => setLiquidBalance(Math.max(0, Number(e.target.value)))}
                    className="form-input"
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      fontSize: '1.1rem',
                      fontWeight: '700',
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      color: '#ffffff'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {[50000, 150000, 300000, 500000, 1000000].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setLiquidBalance(val)}
                      style={{
                        padding: '6px 12px',
                        background: liquidBalance === val ? 'var(--accent-secondary)' : 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        fontSize: '0.78rem',
                        cursor: 'pointer'
                      }}
                    >
                      ₹{(val / 1000).toFixed(0)}k
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="animate-fade-in">
                <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', marginBottom: '12px' }}>
                  Question 3 of 3
                </span>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '6px' }}>Do you have any monthly loan EMIs?</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '18px' }}>
                  Home loan, car loan, education, or personal credit obligations (or 0 if debt-free).
                </p>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
                    Total Monthly EMI (₹)
                  </label>
                  <input
                    type="number"
                    value={monthlyEmi}
                    onChange={(e) => setMonthlyEmi(Math.max(0, Number(e.target.value)))}
                    className="form-input"
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      fontSize: '1.1rem',
                      fontWeight: '700',
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      color: '#ffffff'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  {[0, 10000, 15000, 25000, 45000].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setMonthlyEmi(val)}
                      style={{
                        padding: '6px 12px',
                        background: monthlyEmi === val ? 'var(--accent-warning)' : 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        color: monthlyEmi === val ? '#000000' : '#ffffff',
                        fontWeight: '600',
                        fontSize: '0.78rem',
                        cursor: 'pointer'
                      }}
                    >
                      {val === 0 ? '₹0 (Debt Free)' : `₹${(val / 1000).toFixed(0)}k`}
                    </button>
                  ))}
                </div>

                {monthlyEmi > 0 && (
                  <div className="animate-fade-in" style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
                      Primary Loan Type
                    </label>
                    <select
                      value={loanType}
                      onChange={(e) => setLoanType(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px',
                        background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        fontSize: '0.85rem'
                      }}
                    >
                      <option value="Personal Loan">Personal Loan</option>
                      <option value="Home Loan">Home Loan</option>
                      <option value="Auto / Vehicle Loan">Auto / Vehicle Loan</option>
                      <option value="Education Loan">Education Loan</option>
                      <option value="Credit Card EMI">Credit Card EMI</option>
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Live Deterministic Metric Simulator */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '20px'
          }}>
            <h4 style={{
              fontSize: '0.88rem',
              color: 'var(--text-main)',
              marginBottom: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <Shield size={16} color="var(--accent-secondary)" /> Live Financial State
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Emergency Runway:</span>
                  <span style={{
                    fontWeight: '700',
                    color: runwayMonths >= 6 ? 'var(--accent-success)' : (runwayMonths >= 3 ? '#fbbf24' : '#f87171')
                  }}>
                    {runwayMonths} months
                  </span>
                </div>
                <div style={{
                  height: '6px',
                  borderRadius: '3px',
                  background: 'rgba(255,255,255,0.08)',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(100, (runwayMonths / 6.0) * 100)}%`,
                    background: runwayMonths >= 6 ? 'var(--accent-success)' : (runwayMonths >= 3 ? '#fbbf24' : '#f87171'),
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Debt-to-Income (DTI):</span>
                  <span style={{
                    fontWeight: '700',
                    color: dtiRatio <= 30 ? 'var(--accent-success)' : (dtiRatio <= 45 ? '#fbbf24' : '#f87171')
                  }}>
                    {dtiRatio}%
                  </span>
                </div>
                <div style={{
                  height: '6px',
                  borderRadius: '3px',
                  background: 'rgba(255,255,255,0.08)',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(100, (dtiRatio / 50.0) * 100)}%`,
                    background: dtiRatio <= 30 ? 'var(--accent-success)' : (dtiRatio <= 45 ? '#fbbf24' : '#f87171'),
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              <div style={{
                paddingTop: '12px',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Projected Health Score</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: '800', color: healthScore >= 70 ? 'var(--accent-success)' : '#fbbf24' }}>
                    {healthScore} / 100
                  </div>
                </div>
                <div className="badge" style={{
                  background: healthScore >= 70 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: healthScore >= 70 ? 'var(--accent-success)' : '#fbbf24'
                }}>
                  {healthScore >= 80 ? 'Grade A' : (healthScore >= 65 ? 'Grade B' : 'Grade C')}
                </div>
              </div>
            </div>

            <div style={{
              marginTop: '16px',
              padding: '10px 12px',
              borderRadius: '8px',
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              fontSize: '0.72rem',
              color: 'var(--text-muted)',
              lineHeight: '1.4'
            }}>
              💡 Instant Neo4j bootstrap gives your dashboard immediate intelligence without waiting for statement files.
            </div>
          </div>
        </div>

        {/* Wizard Footer Controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '28px',
          paddingTop: '20px',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          <div>
            {onOpenConnectBank && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onOpenConnectBank();
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-secondary)',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                Or connect bank account via Setu / Upload statement
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            {step > 1 && (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="btn-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <ArrowLeft size={16} /> Back
              </button>
            )}

            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep(step + 1)}
                className="btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Next Step <ArrowRight size={16} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'linear-gradient(135deg, #10b981, #06b6d4)'
                }}
              >
                <CheckCircle2 size={16} />
                {submitting ? 'Calibrating Graph...' : 'Activate Financial Twin'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

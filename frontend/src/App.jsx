import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  LayoutDashboard,
  PieChart as ChartIcon,
  Receipt,
  MessageSquare,
  RefreshCw,
  CheckCircle2,
  TrendingUp,
  Shield,
  LogOut
} from 'lucide-react';
import KPICards from './components/KPICards';
import ExpenseAnalytics from './components/ExpenseAnalytics';
import GoalManager from './components/GoalManager';
import TransactionManager from './components/TransactionManager';
import AssistantChat from './components/AssistantChat';
import LoginScreen from './components/LoginScreen';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [expenses, setExpenses] = useState(null);
  const [debt, setDebt] = useState(null);
  const [emergency, setEmergency] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [user, setUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);

  const fetchAllData = async () => {
    try {
      setRefreshing(true);
      const [sumRes, expRes, debtRes, efRes, txRes] = await Promise.all([
        fetch('/api/finance/summary'),
        fetch('/api/finance/expenses'),
        fetch('/api/finance/debt'),
        fetch('/api/finance/emergency-fund'),
        fetch('/api/transactions')
      ]);

      if (sumRes.ok) setSummary(await sumRes.json());
      if (expRes.ok) setExpenses(await expRes.json());
      if (debtRes.ok) setDebt(await debtRes.json());
      if (efRes.ok) setEmergency(await efRes.json());
      if (txRes.ok) {
        const txData = await txRes.json();
        setTransactions(txData.transactions || []);
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const response = await fetch('/api/auth/session');
        if (!response.ok) return;
        setUser(await response.json());
        await fetchAllData();
      } finally {
        setAuthChecking(false);
        setLoading(false);
      }
    };
    restoreSession();
  }, []);

  const handleLogin = async (credentials) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to sign in');
    setUser(data);
    setLoading(true);
    await fetchAllData();
  };

  const handleSignup = async (payload) => {
    const response = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to create account');
    setUser(data);
    setLoading(true);
    await fetchAllData();
  };

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    setUser(null);
    setSummary(null);
    setExpenses(null);
    setDebt(null);
    setEmergency(null);
    setTransactions([]);
  };

  if (authChecking) {
    return <div style={{ minHeight: '100vh' }} />;
  }

  if (!user) {
    return <LoginScreen onLogin={handleLogin} onSignup={handleSignup} />;
  }

  const handleAddTransaction = async (payload) => {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add transaction');
    }
    // Refresh all financial metrics and transaction table immediately
    await fetchAllData();
  };

  const handleDeleteTransaction = async (txId) => {
    if (!confirm('Are you sure you want to delete this transaction? Account balance will be restored.')) return;
    const res = await fetch(`/api/transactions/${txId}`, {
      method: 'DELETE'
    });
    if (!res.ok) {
      const err = await res.json();
      alert('Delete failed: ' + (err.detail || 'Server error'));
      return;
    }
    await fetchAllData();
  };

  return (
    <div style={{ maxWidth: '1360px', margin: '0 auto', padding: '24px 20px 60px 20px' }}>
      {/* Top Navigation Bar */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '28px',
        paddingBottom: '20px',
        borderBottom: '1px solid var(--border-subtle)',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-glow)'
          }}>
            <Sparkles size={22} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.45rem', fontWeight: '800' }}>
              FinanceGraph <span className="gradient-text">AI</span>
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Dynamic Knowledge Graph & Grounded GraphRAG Assistant
            </p>
          </div>
        </div>

        {/* Navigation Tabs & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            display: 'flex',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            padding: '4px'
          }}>
            <button
              onClick={() => setActiveTab('dashboard')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: '600',
                background: activeTab === 'dashboard' ? 'var(--accent-primary)' : 'transparent',
                color: activeTab === 'dashboard' ? '#ffffff' : 'var(--text-muted)',
                transition: 'all 0.2s ease'
              }}
            >
              <LayoutDashboard size={15} /> Dashboard
            </button>
            <button
              onClick={() => setActiveTab('assistant')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: '600',
                background: activeTab === 'assistant' ? 'var(--accent-primary)' : 'transparent',
                color: activeTab === 'assistant' ? '#ffffff' : 'var(--text-muted)',
                transition: 'all 0.2s ease'
              }}
            >
              <MessageSquare size={15} /> AI Assistant
            </button>
          </div>

          <button
            onClick={fetchAllData}
            className="btn-secondary"
            title="Refresh financial data from Neo4j"
            style={{ padding: '8px 12px' }}
          >
            <RefreshCw size={15} className={refreshing ? 'glow-pulse' : ''} />
          </button>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.84rem'
          }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-success)' }} />
            <span style={{ fontWeight: '600' }}>{user.name || user.username}</span>
          </div>
          <button onClick={handleLogout} className="btn-secondary" title="Sign out" style={{ padding: '8px 12px' }}>
            <LogOut size={15} />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-muted)' }}>
          <Sparkles size={32} color="var(--accent-primary)" className="glow-pulse" style={{ marginBottom: '12px' }} />
          <div>Connecting to Neo4j Knowledge Graph & Loading Financial Engine...</div>
        </div>
      ) : (
        <>
          {activeTab === 'dashboard' && (
            <div className="animate-fade-in">
              {/* Primary KPI Summary Row */}
              <KPICards summary={summary} debt={debt} runway={emergency} />

              {/* Two-Column Analytics Row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
                <ExpenseAnalytics expenses={expenses} />
                <GoalManager summary={summary} debt={debt} emergency={emergency} />
              </div>

              {/* Full-Width Dynamic Transaction Ledger */}
              <TransactionManager
                transactions={transactions}
                onAddTransaction={handleAddTransaction}
                onDeleteTransaction={handleDeleteTransaction}
              />
            </div>
          )}

          {activeTab === 'assistant' && (
            <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
              <AssistantChat />

              {/* Context Summary Sidebar */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="glass-card" style={{ padding: '18px' }}>
                  <h4 style={{ fontSize: '0.92rem', color: 'var(--text-main)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Shield size={16} color="var(--accent-success)" /> Deterministic Grounding
                  </h4>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                    Every answer is computed by the mathematical engine and verified against the Neo4j Knowledge Graph. The LLM explains only verified facts.
                  </p>
                </div>

                <div className="glass-card" style={{ padding: '18px' }}>
                  <h4 style={{ fontSize: '0.92rem', color: 'var(--text-main)', marginBottom: '10px' }}>
                    Current Graph State
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>User Profile:</span>
                      <span style={{ color: 'var(--text-main)', fontWeight: '600' }}>{user.username} ({user.user_id})</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Account Balance:</span>
                      <span style={{ color: '#34d399', fontWeight: '600' }}>₹{(summary?.accounts?.[0]?.balance ?? 0).toLocaleString()}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Monthly Expenses:</span>
                      <span style={{ color: '#f87171', fontWeight: '600' }}>₹{(summary?.expenses ?? 0).toLocaleString()}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Pending EMI:</span>
                      <span style={{ color: '#fbbf24', fontWeight: '600' }}>₹{(debt?.monthly_emi ?? 0).toLocaleString()}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Emergency Buffer:</span>
                      <span style={{ color: 'var(--accent-secondary)', fontWeight: '600' }}>₹{(summary?.recommended_emergency_fund ?? 0).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

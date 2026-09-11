import React, { useState } from 'react';
import { LockKeyhole, Sparkles, UserPlus, User, Wallet, LogIn } from 'lucide-react';

export default function LoginScreen({ onLogin, onSignup }) {
  const [mode, setMode] = useState('login'); // 'login' or 'signup'
  const [username, setUsername] = useState('Rahul');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [initialBalance, setInitialBalance] = useState('25000');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      if (mode === 'login') {
        await onLogin({ username, password });
      } else {
        if (!username || username.trim().length < 3) {
          throw new Error('Username must be at least 3 characters');
        }
        if (!password || password.length < 4) {
          throw new Error('Password must be at least 4 characters');
        }
        await onSignup({
          username: username.trim(),
          password,
          name: name.trim() || username.trim(),
          initial_balance: parseFloat(initialBalance) || 0
        });
      }
    } catch (err) {
      setError(err.message || (mode === 'login' ? 'Unable to sign in' : 'Unable to create account'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '24px' }}>
      <div className="glass-card" style={{ width: '100%', maxWidth: '440px', display: 'grid', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '44px', height: '44px', display: 'grid', placeItems: 'center', borderRadius: '12px', background: 'var(--accent-primary)', boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)' }}>
            <Sparkles size={22} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.35rem', fontWeight: '700', letterSpacing: '-0.02em' }}>FinanceGraph AI</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>
              {mode === 'login' ? 'Sign in to your financial workspace' : 'Create your graph-backed financial account'}
            </p>
          </div>
        </div>

        {/* Mode Switcher Tabs */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: '10px',
          padding: '4px',
          gap: '4px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <button
            type="button"
            onClick={() => { setMode('login'); setError(''); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: mode === 'login' ? '600' : '400',
              background: mode === 'login' ? 'var(--accent-primary)' : 'transparent',
              color: mode === 'login' ? '#ffffff' : 'var(--text-muted)',
              transition: 'all 0.2s ease'
            }}
          >
            <LogIn size={15} /> Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('signup'); setError(''); if (username === 'Rahul') setUsername(''); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: mode === 'signup' ? '600' : '400',
              background: mode === 'signup' ? 'var(--accent-primary)' : 'transparent',
              color: mode === 'signup' ? '#ffffff' : 'var(--text-muted)',
              transition: 'all 0.2s ease'
            }}
          >
            <UserPlus size={15} /> Create Account
          </button>
        </div>

        <form onSubmit={submit} style={{ display: 'grid', gap: '14px' }}>
          {mode === 'signup' && (
            <label style={{ display: 'grid', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Full Name
              <div style={{ position: 'relative' }}>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. John Doe"
                  style={{ width: '100%' }}
                />
              </div>
            </label>
          )}

          <label style={{ display: 'grid', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder={mode === 'signup' ? "Choose a unique username" : "Enter username"}
              required
            />
          </label>

          <label style={{ display: 'grid', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? "current-password" : "new-password"}
              placeholder={mode === 'signup' ? "Minimum 4 characters" : "Enter password"}
              required
            />
          </label>

          {mode === 'signup' && (
            <label style={{ display: 'grid', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Opening Bank Balance (₹)
              <input
                type="number"
                min="0"
                step="100"
                value={initialBalance}
                onChange={(e) => setInitialBalance(e.target.value)}
                placeholder="25000"
              />
            </label>
          )}

          {error && (
            <p role="alert" style={{
              color: 'var(--accent-danger)',
              fontSize: '0.84rem',
              background: 'rgba(239, 68, 68, 0.1)',
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid rgba(239, 68, 68, 0.2)'
            }}>
              {error}
            </p>
          )}

          <button
            className="btn-primary"
            type="submit"
            disabled={submitting}
            style={{
              justifyContent: 'center',
              marginTop: '6px',
              padding: '12px'
            }}
          >
            {mode === 'login' ? (
              <><LockKeyhole size={16} /> {submitting ? 'Signing in...' : 'Sign in'}</>
            ) : (
              <><UserPlus size={16} /> {submitting ? 'Creating account...' : 'Sign Up & Get Started'}</>
            )}
          </button>
        </form>

        <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {mode === 'login' ? (
            <p>
              Demo user: <strong>Rahul</strong> &bull; Password: <strong>demo1234</strong>
            </p>
          ) : (
            <p>
              Your personal graph, starter categories, and primary account will be generated instantly.
            </p>
          )}
        </div>
      </div>
    </main>
  );
}

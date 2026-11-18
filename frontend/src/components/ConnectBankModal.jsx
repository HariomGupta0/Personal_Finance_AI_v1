import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Building,
  CheckCircle2,
  Lock,
  ShieldCheck,
  AlertCircle,
  FileText,
  Upload,
  ArrowRight,
  RefreshCw,
  X,
  Smartphone,
  KeyRound,
  ExternalLink
} from 'lucide-react';

export default function ConnectBankModal({ isOpen, onClose, onSyncComplete }) {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState('setu'); // 'setu' or 'upload'

  // --- SETU TAB STATE ---
  const [banks, setBanks] = useState([]);
  const [selectedBank, setSelectedBank] = useState('HDFC');
  const [phone, setPhone] = useState('9999999999');
  const [setuStep, setSetuStep] = useState('SELECT'); // 'SELECT', 'CONSENT_OTP', 'SYNCING', 'SUCCESS'
  const [consentInfo, setConsentInfo] = useState(null);
  const [otp, setOtp] = useState('123456');
  const [syncResult, setSyncResult] = useState(null);
  const [setuLoading, setSetuLoading] = useState(false);
  const [setuError, setSetuError] = useState(null);

  // --- UPLOAD TAB STATE ---
  const [file, setFile] = useState(null);
  const [password, setPassword] = useState('');
  const [isPdf, setIsPdf] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Fetch banks on mount
  useEffect(() => {
    fetch('/api/import/aa/banks')
      .then((r) => r.json())
      .then((d) => {
        if (d.banks) setBanks(d.banks);
      })
      .catch((err) => console.error('Failed to load banks:', err));
  }, []);

  // --- SETU FLOW HANDLERS ---
  const handleInitiateSetu = async () => {
    try {
      setSetuLoading(true);
      setSetuError(null);

      // 1. Discover Accounts
      const discRes = await fetch('/api/import/aa/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, fip_id: selectedBank })
      });
      if (!discRes.ok) throw new Error('Failed to discover bank accounts');
      const discData = await discRes.json();
      const discoveredAcc = discData.accounts?.[0]?.account_id || `ACC_${selectedBank}_4102`;

      // 2. Create Consent Request
      const consentRes = await fetch('/api/import/aa/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone,
          fip_id: selectedBank,
          account_id: discoveredAcc
        })
      });
      if (!consentRes.ok) throw new Error('Failed to initiate Setu consent flow');
      const consentData = await consentRes.json();

      setConsentInfo({
        ...consentData,
        account_id: discoveredAcc,
        masked_number: discData.accounts?.[0]?.masked_number || 'XXXX-XXXX-4102'
      });
      setSetuStep('CONSENT_OTP');
    } catch (err) {
      console.error('Setu init error:', err);
      setSetuError(err.message);
    } finally {
      setSetuLoading(false);
    }
  };

  const handleVerifyOtpAndSync = async () => {
    try {
      setSetuLoading(true);
      setSetuError(null);
      setSetuStep('SYNCING');

      const res = await fetch('/api/import/aa/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone,
          otp,
          account_id: consentInfo?.account_id || `ACC_${selectedBank}_4102`,
          fip_id: selectedBank,
          consent_id: consentInfo?.consent_id || ''
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'OTP verification or sync failed');
      }

      const data = await res.json();
      setSyncResult(data);
      setSetuStep('SUCCESS');
      if (onSyncComplete) onSyncComplete();
    } catch (err) {
      console.error('Setu sync error:', err);
      setSetuError(err.message);
      setSetuStep('CONSENT_OTP');
    } finally {
      setSetuLoading(false);
    }
  };

  // --- UPLOAD FLOW HANDLERS ---
  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;
    setFile(selectedFile);
    setIsPdf(selectedFile.name.toLowerCase().endsWith('.pdf'));
    setUploadError(null);
    setPreviewData(null);
  };

  const handleProcessFile = async () => {
    if (!file) return;
    try {
      setUploadLoading(true);
      setUploadError(null);

      const formData = new FormData();
      formData.append('file', file);
      if (password) {
        formData.append('password', password);
      }

      const res = await fetch('/api/import/csv', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.detail?.error_code === 'PASSWORD_REQUIRED') {
          throw new Error('This PDF statement is password-protected. Please enter your statement password below.');
        } else if (data.detail?.error_code === 'INCORRECT_PASSWORD') {
          throw new Error('Incorrect PDF password. Please re-enter your password.');
        } else {
          throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to parse statement');
        }
      }

      setPreviewData(data);
    } catch (err) {
      console.error('File parse error:', err);
      setUploadError(err.message);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleConfirmUpload = async () => {
    if (!previewData?.accepted_rows?.length && !previewData?.valid_rows?.length) return;
    try {
      setConfirming(true);
      setUploadError(null);

      const rowsToConfirm = previewData.accepted_rows || previewData.valid_rows;

      const res = await fetch('/api/import/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rows: rowsToConfirm
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Confirmation failed');
      }

      setUploadSuccess(true);
      if (onSyncComplete) onSyncComplete();
    } catch (err) {
      console.error('Confirm error:', err);
      setUploadError(err.message);
    } finally {
      setConfirming(false);
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
        maxWidth: '740px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '30px',
        borderRadius: '20px',
        border: '1px solid rgba(99, 102, 241, 0.3)',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #004c8f, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.3)'
          }}>
            <Building size={22} color="#ffffff" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: '800' }}>
              Connect Your Bank Account
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Live consent via Setu Account Aggregator or secure statement upload.
            </p>
          </div>
        </div>

        {/* Tab Selection */}
        <div style={{
          display: 'flex',
          background: 'rgba(255, 255, 255, 0.05)',
          padding: '4px',
          borderRadius: '10px',
          marginBottom: '24px'
        }}>
          <button
            type="button"
            onClick={() => setActiveTab('setu')}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              background: activeTab === 'setu' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'setu' ? '#ffffff' : 'var(--text-muted)',
              transition: 'all 0.2s ease'
            }}
          >
            <Sparkles size={16} /> Instant Connect (Setu AA)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('upload')}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              background: activeTab === 'upload' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'upload' ? '#ffffff' : 'var(--text-muted)',
              transition: 'all 0.2s ease'
            }}
          >
            <Upload size={16} /> Statement Upload (PDF / CSV)
          </button>
        </div>

        {/* ============================================================== */}
        {/* TAB 1: SETU ACCOUNT AGGREGATOR */}
        {/* ============================================================== */}
        {activeTab === 'setu' && (
          <div>
            {setuError && (
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
                <span>{setuError}</span>
              </div>
            )}

            {/* STEP 1: SELECT BANK & MOBILE */}
            {setuStep === 'SELECT' && (
              <div className="animate-fade-in">
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Select Financial Information Provider (Bank)
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '20px' }}>
                  {(banks.length > 0 ? banks : [
                    { id: 'HDFC', name: 'HDFC Bank', color: '#004c8f' },
                    { id: 'SBI', name: 'State Bank of India', color: '#280071' },
                    { id: 'ICICI', name: 'ICICI Bank', color: '#f37e20' },
                    { id: 'AXIS', name: 'Axis Bank', color: '#97144d' }
                  ]).map((b) => (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => setSelectedBank(b.id)}
                      style={{
                        padding: '14px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        background: selectedBank === b.id ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                        border: `1.5px solid ${selectedBank === b.id ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                        borderRadius: '12px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <div style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        background: b.color || '#6366f1'
                      }} />
                      <div>
                        <div style={{ fontWeight: '700', fontSize: '0.9rem', color: '#ffffff' }}>{b.name}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>RBI-Regulated FIP</div>
                      </div>
                    </button>
                  ))}
                </div>

                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Registered Mobile Number
                </label>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="Enter 10-digit mobile number"
                    style={{
                      flex: 1,
                      padding: '12px 14px',
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      color: '#ffffff',
                      fontSize: '0.95rem'
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleInitiateSetu}
                    disabled={setuLoading || !phone}
                    className="btn-primary"
                    style={{ padding: '0 20px', display: 'flex', alignItems: 'center', gap: '8px' }}
                  >
                    {setuLoading ? <RefreshCw size={16} className="glow-pulse" /> : <ArrowRight size={16} />}
                    Connect
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Developer Sandbox Personas:</span>
                  <button
                    type="button"
                    onClick={() => setPhone('9999999999')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--accent-secondary)',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      textDecoration: 'underline'
                    }}
                  >
                    9999999999 (High Salaried)
                  </button>
                  <button
                    type="button"
                    onClick={() => setPhone('8888888888')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--accent-secondary)',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      textDecoration: 'underline'
                    }}
                  >
                    8888888888 (Overdraft Profile)
                  </button>
                </div>

                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px',
                  background: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  borderRadius: '10px',
                  fontSize: '0.76rem',
                  color: 'var(--text-muted)'
                }}>
                  <ShieldCheck size={18} color="var(--accent-success)" />
                  <span>
                    RBI-regulated Setu Account Aggregator. Data is encrypted end-to-end. We never see or store your net banking credentials.
                  </span>
                </div>
              </div>
            )}

            {/* STEP 2: CONSENT CONFIRMATION & OTP INPUT */}
            {setuStep === 'CONSENT_OTP' && (
              <div className="animate-fade-in">
                <div style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '14px',
                  padding: '18px',
                  marginBottom: '20px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Lock size={16} color="var(--accent-secondary)" />
                      <span style={{ fontWeight: '700', fontSize: '0.9rem' }}>Digital Consent Request</span>
                    </div>
                    <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8' }}>
                      Setu FIU Sandbox
                    </span>
                  </div>

                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div>Bank: <strong style={{ color: '#ffffff' }}>{consentInfo?.bank_name || selectedBank}</strong></div>
                    <div>Account: <strong style={{ color: '#ffffff' }}>{consentInfo?.masked_number}</strong></div>
                    <div>Scope: <strong style={{ color: 'var(--accent-secondary)' }}>Read-only 90-day transactions</strong></div>
                  </div>
                </div>

                <div style={{ marginBottom: '18px' }}>
                  <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    Enter 6-Digit OTP received on +91 {phone}
                  </label>
                  <input
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    maxLength={6}
                    placeholder="123456"
                    style={{
                      width: '100%',
                      padding: '14px',
                      fontSize: '1.25rem',
                      fontWeight: '800',
                      letterSpacing: '8px',
                      textAlign: 'center',
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      color: '#ffffff'
                    }}
                  />
                  <div style={{ fontSize: '0.75rem', color: 'var(--accent-success)', marginTop: '6px', textAlign: 'center' }}>
                    💡 Sandbox Test OTP: <strong>123456</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setSetuStep('SELECT')}
                    className="btn-secondary"
                    style={{ flex: 1 }}
                  >
                    Change Bank
                  </button>
                  <button
                    type="button"
                    onClick={handleVerifyOtpAndSync}
                    disabled={setuLoading || otp.length < 4}
                    className="btn-primary"
                    style={{
                      flex: 2,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      background: 'linear-gradient(135deg, #10b981, #06b6d4)'
                    }}
                  >
                    <CheckCircle2 size={16} /> Authorize & Sync Data
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: SYNCING IN PROGRESS */}
            {setuStep === 'SYNCING' && (
              <div className="animate-fade-in" style={{ textAlign: 'center', padding: '30px 10px' }}>
                <RefreshCw size={36} color="var(--accent-primary)" className="glow-pulse" style={{ marginBottom: '16px' }} />
                <h3 style={{ fontSize: '1.15rem', marginBottom: '8px' }}>Connecting to Setu FIU Network...</h3>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', maxWidth: '420px', margin: '0 auto 20px auto' }}>
                  Decrypting verified 90-day bank statements, running SHA-256 fingerprint deduplication, and enriching merchant categories.
                </p>
                <div style={{
                  maxWidth: '360px',
                  margin: '0 auto',
                  textAlign: 'left',
                  fontSize: '0.78rem',
                  color: 'var(--text-dim)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}>
                  <div>✓ Verified consent token with Setu Sandbox</div>
                  <div>✓ Fetched 90-day encrypted statement bundle</div>
                  <div>⏳ Categorizing Swiggy, Uber, Rent & Salary into Neo4j...</div>
                </div>
              </div>
            )}

            {/* STEP 4: SUCCESS */}
            {setuStep === 'SUCCESS' && (
              <div className="animate-fade-in" style={{ textAlign: 'center', padding: '20px 10px' }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px auto',
                  border: '1px solid rgba(16, 185, 129, 0.3)'
                }}>
                  <CheckCircle2 size={32} color="var(--accent-success)" />
                </div>
                <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>Bank Connected Successfully!</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
                  {syncResult?.message || 'Your account is live and fully synchronized.'}
                </p>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '12px',
                  background: 'rgba(0, 0, 0, 0.3)',
                  padding: '16px',
                  borderRadius: '12px',
                  marginBottom: '24px',
                  textAlign: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--accent-success)' }}>
                      {syncResult?.synced_transactions ?? 42}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Synced Txns</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--accent-secondary)' }}>
                      {syncResult?.duplicate_count ?? 0}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Deduplicated</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: '800', color: '#818cf8' }}>
                      1
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Account Linked</div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={onClose}
                  className="btn-primary"
                  style={{ width: '100%', padding: '12px' }}
                >
                  View Updated Dashboard
                </button>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 2: SMART STATEMENT UPLOAD (PDF / CSV) */}
        {/* ============================================================== */}
        {activeTab === 'upload' && (
          <div>
            {uploadError && (
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
                <span>{uploadError}</span>
              </div>
            )}

            {!previewData && !uploadSuccess && (
              <div className="animate-fade-in">
                {/* Drag and Drop Zone */}
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) handleFileChange(e.dataTransfer.files[0]);
                  }}
                  style={{
                    border: '2px dashed var(--border-subtle)',
                    borderRadius: '14px',
                    padding: '36px 20px',
                    textAlign: 'center',
                    background: 'rgba(255, 255, 255, 0.02)',
                    cursor: 'pointer',
                    marginBottom: '16px',
                    transition: 'border-color 0.2s ease'
                  }}
                  onClick={() => document.getElementById('statement-file-input')?.click()}
                >
                  <input
                    id="statement-file-input"
                    type="file"
                    accept=".csv,.tsv,.txt,.pdf"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
                    }}
                  />
                  <FileText size={36} color="var(--accent-secondary)" style={{ marginBottom: '12px' }} />
                  <div style={{ fontWeight: '700', fontSize: '0.95rem', color: '#ffffff', marginBottom: '4px' }}>
                    {file ? file.name : 'Click to browse or drop statement here'}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Supports official e-statements (.PDF, .CSV) from HDFC, SBI, ICICI, Axis
                  </div>
                </div>

                {/* Password helper box for PDF */}
                {isPdf && (
                  <div className="animate-fade-in" style={{
                    background: 'rgba(245, 158, 11, 0.1)',
                    border: '1px solid rgba(245, 158, 11, 0.25)',
                    padding: '14px',
                    borderRadius: '10px',
                    marginBottom: '16px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <KeyRound size={16} color="var(--accent-warning)" />
                      <span style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fbbf24' }}>
                        Password-Protected PDF Statement?
                      </span>
                    </div>
                    <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                      Most Indian banks protect statements with your PAN (e.g., ABCDE1234F) or Date of Birth (DDMMYYYY).
                    </p>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter statement password (if encrypted)"
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        background: 'rgba(0, 0, 0, 0.3)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleProcessFile}
                  disabled={uploadLoading || !file}
                  className="btn-primary"
                  style={{
                    width: '100%',
                    padding: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  {uploadLoading ? (
                    <>
                      <RefreshCw size={16} className="glow-pulse" />
                      Decrypting & Parsing Statement...
                    </>
                  ) : (
                    <>
                      <Upload size={16} /> Parse Statement
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Preview State */}
            {previewData && !uploadSuccess && (
              <div className="animate-fade-in">
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '14px'
                }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: '700' }}>
                    Statement Preview ({previewData.stats?.accepted_count ?? previewData.valid_rows?.length ?? 0} Transactions)
                  </h4>
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewData(null);
                      setFile(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-dim)',
                      fontSize: '0.78rem',
                      cursor: 'pointer'
                    }}
                  >
                    Select different file
                  </button>
                </div>

                <div style={{
                  maxHeight: '240px',
                  overflowY: 'auto',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  marginBottom: '18px'
                }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ background: 'rgba(255, 255, 255, 0.05)', textAlign: 'left' }}>
                        <th style={{ padding: '8px 12px' }}>Date</th>
                        <th style={{ padding: '8px 12px' }}>Description</th>
                        <th style={{ padding: '8px 12px' }}>Category</th>
                        <th style={{ padding: '8px 12px', textAlign: 'right' }}>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(previewData.accepted_rows || previewData.valid_rows || []).slice(0, 8).map((r, i) => (
                        <tr key={i} style={{ borderTop: '1px solid rgba(255, 255, 255, 0.04)' }}>
                          <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>{r.date}</td>
                          <td style={{ padding: '8px 12px', fontWeight: '600', color: '#ffffff' }}>
                            {r.clean_merchant || r.description}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                              {r.category || 'General'}
                            </span>
                          </td>
                          <td style={{
                            padding: '8px 12px',
                            textAlign: 'right',
                            fontWeight: '700',
                            color: r.type === 'INCOME' ? 'var(--accent-success)' : '#ffffff'
                          }}>
                            {r.type === 'INCOME' ? '+' : '-'}₹{(r.amount || 0).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <button
                  type="button"
                  onClick={handleConfirmUpload}
                  disabled={confirming}
                  className="btn-primary"
                  style={{
                    width: '100%',
                    padding: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    background: 'linear-gradient(135deg, #10b981, #06b6d4)'
                  }}
                >
                  <CheckCircle2 size={16} />
                  {confirming ? 'Persisting to Knowledge Graph...' : 'Confirm & Save to Graph'}
                </button>
              </div>
            )}

            {/* Success State */}
            {uploadSuccess && (
              <div className="animate-fade-in" style={{ textAlign: 'center', padding: '30px 10px' }}>
                <CheckCircle2 size={44} color="var(--accent-success)" style={{ marginBottom: '14px' }} />
                <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Statement Imported Successfully!</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
                  Transactions have been categorized, deduplicated, and linked to your financial twin.
                </p>
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-primary"
                  style={{ padding: '12px 32px' }}
                >
                  Return to Dashboard
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

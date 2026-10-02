import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  Image,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  ChevronDown,
  ChevronUp,
  Loader2,
  Eye,
  Send,
  RefreshCw,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

const sym = '₹';
const fmt = (n) => parseFloat(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });

function Badge({ label, color }) {
  const colors = {
    success: { bg: 'rgba(16,185,129,0.15)', color: '#34d399', border: 'rgba(16,185,129,0.3)' },
    danger:  { bg: 'rgba(239,68,68,0.15)',  color: '#f87171', border: 'rgba(239,68,68,0.3)' },
    warning: { bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: 'rgba(245,158,11,0.3)' },
    info:    { bg: 'rgba(99,102,241,0.15)', color: '#818cf8', border: 'rgba(99,102,241,0.3)' },
  };
  const s = colors[color] || colors.info;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 9999, fontSize: '0.72rem',
      fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase',
      background: s.bg, color: s.color, border: `1px solid ${s.border}`
    }}>
      {label}
    </span>
  );
}

function Spinner() {
  return (
    <span style={{ display: 'inline-flex', animation: 'spin 0.8s linear infinite' }}>
      <Loader2 size={16} />
    </span>
  );
}

function Alert({ type, children }) {
  const cfg = {
    error:   { bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.3)',   color: '#f87171' },
    warning: { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)',  color: '#fbbf24' },
    success: { bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.3)',  color: '#34d399' },
    info:    { bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.3)',  color: '#818cf8' },
  };
  const c = cfg[type] || cfg.info;
  return (
    <div style={{
      background: c.bg, border: `1px solid ${c.border}`, borderRadius: 10,
      padding: '10px 14px', fontSize: '0.82rem', color: c.color, lineHeight: 1.5,
      display: 'flex', gap: 8, alignItems: 'flex-start'
    }}>
      {type === 'error'   && <XCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />}
      {type === 'warning' && <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }} />}
      {type === 'success' && <CheckCircle2 size={15} style={{ flexShrink: 0, marginTop: 1 }} />}
      <span>{children}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function Steps({ current }) {
  const steps = ['Upload', 'Preview', 'Confirm', 'Done'];
  return (
    <div style={{ display: 'flex', gap: 0, marginBottom: 24, alignItems: 'center' }}>
      {steps.map((s, i) => {
        const done    = i < current;
        const active  = i === current;
        const pending = i > current;
        return (
          <React.Fragment key={s}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700,
                background: done ? '#10b981' : active ? '#6366f1' : 'rgba(255,255,255,0.08)',
                color: (done || active) ? '#fff' : '#6b7280',
                border: active ? '2px solid rgba(99,102,241,0.5)' : '2px solid transparent',
                transition: 'all 0.3s ease',
              }}>
                {done ? <CheckCircle2 size={14} /> : i + 1}
              </div>
              <span style={{ fontSize: '0.7rem', color: active ? '#c7d2fe' : done ? '#34d399' : '#6b7280', fontWeight: active ? 700 : 400 }}>
                {s}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div style={{ flex: 1, height: 2, background: done ? '#10b981' : 'rgba(255,255,255,0.07)', margin: '-16px 6px 0 6px', transition: 'background 0.3s' }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// File drop zone
// ---------------------------------------------------------------------------

function DropZone({ mode, onFile, disabled }) {
  const inputRef = useRef();
  const [dragging, setDragging] = useState(false);
  const accept = mode === 'csv' ? '.csv,.tsv,.txt' : '.jpg,.jpeg,.png,.webp,.gif';
  const label  = mode === 'csv'
    ? 'Drop your bank statement CSV here or click to browse'
    : 'Drop a receipt / UPI screenshot here or click to browse';
  const hint  = mode === 'csv'
    ? 'Supports: debit/credit, narration/withdrawal, standard HDFC/SBI/ICICI formats · Max 5 MB'
    : 'Supports: JPEG, PNG, WebP, GIF · Max 10 MB';

  const handle = (files) => {
    if (files && files[0]) onFile(files[0]);
  };

  return (
    <div
      onClick={() => !disabled && inputRef.current.click()}
      onDragOver={e => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); if (!disabled) handle(e.dataTransfer.files); }}
      style={{
        border: `2px dashed ${dragging ? '#6366f1' : 'rgba(255,255,255,0.12)'}`,
        borderRadius: 14, padding: '40px 24px', textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: dragging ? 'rgba(99,102,241,0.07)' : 'rgba(255,255,255,0.02)',
        transition: 'all 0.2s ease', opacity: disabled ? 0.5 : 1,
      }}
    >
      <input ref={inputRef} type="file" accept={accept} style={{ display: 'none' }}
        onChange={e => handle(e.target.files)} />
      <div style={{ marginBottom: 12, color: '#6366f1' }}>
        {mode === 'csv' ? <FileText size={36} /> : <Image size={36} />}
      </div>
      <p style={{ color: 'var(--text-main)', fontWeight: 600, marginBottom: 6 }}>{label}</p>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>{hint}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Preview table for parsed CSV rows
// ---------------------------------------------------------------------------

function PreviewTable({ rows, selectedIds, onToggle, onToggleAll, onEdit }) {
  const allSelected = rows.every(r => selectedIds.has(r._id));
  const dupCount    = rows.filter(r => r.duplicate_status === 'POSSIBLE_DUPLICATE').length;
  const confirmedDup = rows.filter(r => r.duplicate_status === 'CONFIRMED_DUPLICATE').length;

  return (
    <div>
      {dupCount > 0 && (
        <Alert type="warning">
          {dupCount} row{dupCount > 1 ? 's' : ''} may already exist in your ledger (flagged as possible duplicates).
          Review carefully before importing.
        </Alert>
      )}
      {confirmedDup > 0 && (
        <div style={{ marginTop: 8 }}>
          <Alert type="error">
            {confirmedDup} row{confirmedDup > 1 ? 's' : ''} match existing transactions by reference ID and are pre-deselected.
          </Alert>
        </div>
      )}

      <div style={{ overflowX: 'auto', marginTop: 14 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.72rem', textTransform: 'uppercase' }}>
              <th style={{ padding: '8px 10px' }}>
                <input type="checkbox" checked={allSelected}
                  onChange={() => onToggleAll(!allSelected)}
                  style={{ cursor: 'pointer', width: 14, height: 14 }} />
              </th>
              <th style={{ padding: '8px 10px' }}>Type</th>
              <th style={{ padding: '8px 10px' }}>Date</th>
              <th style={{ padding: '8px 10px' }}>Description</th>
              <th style={{ padding: '8px 10px' }}>Category</th>
              <th style={{ padding: '8px 10px', textAlign: 'right' }}>Amount</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Edit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isSelected = selectedIds.has(row._id);
              const isDup      = row.duplicate_status === 'POSSIBLE_DUPLICATE';
              const isConfDup  = row.duplicate_status === 'CONFIRMED_DUPLICATE';
              const isIncome   = row.type === 'INCOME';

              return (
                <tr key={row._id}
                  style={{
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    background: isDup ? 'rgba(245,158,11,0.04)' : isConfDup ? 'rgba(239,68,68,0.04)' : 'transparent',
                    opacity: isConfDup ? 0.55 : 1,
                    transition: 'background 0.15s',
                  }}
                >
                  <td style={{ padding: '10px 10px' }}>
                    <input type="checkbox" checked={isSelected && !isConfDup}
                      disabled={isConfDup}
                      onChange={() => !isConfDup && onToggle(row._id)}
                      style={{ cursor: isConfDup ? 'not-allowed' : 'pointer', width: 14, height: 14 }} />
                  </td>
                  <td style={{ padding: '10px 10px' }}>
                    <span className={`badge ${isIncome ? 'badge-success' : 'badge-danger'}`}>
                      {isIncome ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                      {row.type}
                    </span>
                  </td>
                  <td style={{ padding: '10px 10px', color: 'var(--text-muted)' }}>{row.date}</td>
                  <td style={{ padding: '10px 10px', color: 'var(--text-main)', maxWidth: 220 }}>
                    <span title={row.description} style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {row.description}
                    </span>
                  </td>
                  <td style={{ padding: '10px 10px' }}>
                    <span className="badge badge-info">{row.category || 'General'}</span>
                  </td>
                  <td style={{ padding: '10px 10px', textAlign: 'right', fontWeight: 600, color: isIncome ? '#34d399' : '#f87171' }}>
                    {isIncome ? '+' : '-'}{sym}{fmt(row.amount)}
                  </td>
                  <td style={{ padding: '10px 10px', textAlign: 'center' }}>
                    {isConfDup && <Badge label="Duplicate" color="danger" />}
                    {isDup     && <Badge label="Review"    color="warning" />}
                    {!isDup && !isConfDup && <Badge label="OK" color="success" />}
                  </td>
                  <td style={{ padding: '10px 10px', textAlign: 'center' }}>
                    <button
                      onClick={() => onEdit(row._id)}
                      title="Edit this row"
                      style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 4 }}
                    >
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline row editor
// ---------------------------------------------------------------------------

function RowEditor({ row, onSave, onCancel }) {
  const [form, setForm] = useState({ ...row });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const inputStyle = {
    background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)',
    borderRadius: 8, padding: '6px 10px', color: 'var(--text-main)',
    fontSize: '0.82rem', outline: 'none', width: '100%',
  };

  return (
    <div style={{
      background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.2)',
      borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 12
    }}>
      <p style={{ fontSize: '0.82rem', color: '#818cf8', fontWeight: 600 }}>✏️ Edit Transaction</p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Date (YYYY-MM-DD)</label>
          <input style={inputStyle} value={form.date || ''} onChange={e => set('date', e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Amount</label>
          <input style={inputStyle} type="number" step="0.01" min="0.01" value={form.amount || ''} onChange={e => set('amount', parseFloat(e.target.value))} />
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Description</label>
          <input style={inputStyle} value={form.description || ''} onChange={e => set('description', e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Type</label>
          <select style={inputStyle} value={form.type} onChange={e => set('type', e.target.value)}>
            <option value="EXPENSE">EXPENSE</option>
            <option value="INCOME">INCOME</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Category</label>
          <input style={inputStyle} value={form.category || ''} onChange={e => set('category', e.target.value)} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button className="btn-secondary" style={{ padding: '6px 14px', fontSize: '0.8rem' }} onClick={onCancel}>Cancel</button>
        <button className="btn-primary"   style={{ padding: '6px 14px', fontSize: '0.8rem' }} onClick={() => onSave(form)}>Save</button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Image review form
// ---------------------------------------------------------------------------

function ImageReviewForm({ extraction, onSave, onCancel }) {
  const [form, setForm] = useState({
    date: extraction.date || '',
    amount: extraction.amount || '',
    description: extraction.description || '',
    type: extraction.type || 'EXPENSE',
    category: '',
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const inputStyle = {
    background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)',
    borderRadius: 8, padding: '6px 10px', color: 'var(--text-main)',
    fontSize: '0.82rem', outline: 'none', width: '100%',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {extraction.warnings && extraction.warnings.length > 0 && (
        <Alert type="warning">
          {extraction.warnings.map((w, i) => <div key={i}>• {w}</div>)}
        </Alert>
      )}
      <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        Review and correct the extracted fields before importing.
        Fields highlighted with a ⚠️ require special attention.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>
            {!form.date ? '⚠️ ' : ''}Date (YYYY-MM-DD)
          </label>
          <input style={{ ...inputStyle, borderColor: !form.date ? 'rgba(245,158,11,0.4)' : undefined }}
            value={form.date} onChange={e => set('date', e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>
            {!form.amount ? '⚠️ ' : ''}Amount (₹)
          </label>
          <input style={{ ...inputStyle, borderColor: !form.amount ? 'rgba(245,158,11,0.4)' : undefined }}
            type="number" step="0.01" min="0.01"
            value={form.amount} onChange={e => set('amount', parseFloat(e.target.value))} />
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>
            {!form.description ? '⚠️ ' : ''}Merchant / Recipient
          </label>
          <input style={inputStyle} value={form.description}
            onChange={e => set('description', e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Type</label>
          <select style={inputStyle} value={form.type} onChange={e => set('type', e.target.value)}>
            <option value="EXPENSE">EXPENSE</option>
            <option value="INCOME">INCOME</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: 4, display: 'block' }}>Category (optional)</label>
          <input style={inputStyle} value={form.category} onChange={e => set('category', e.target.value)} placeholder="e.g. Food" />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button className="btn-secondary" style={{ padding: '6px 14px', fontSize: '0.8rem' }} onClick={onCancel}>Cancel</button>
        <button className="btn-primary"   style={{ padding: '6px 14px', fontSize: '0.8rem' }}
          disabled={!form.amount || !form.date || !form.description}
          onClick={() => onSave(form)}>
          Confirm &amp; Import
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result summary after confirm
// ---------------------------------------------------------------------------

function ResultSummary({ result, onReset }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ textAlign: 'center', padding: '24px 0' }}>
        {result.status === 'SUCCESS' ? (
          <CheckCircle2 size={48} color="#10b981" />
        ) : result.status === 'PARTIAL' ? (
          <AlertTriangle size={48} color="#f59e0b" />
        ) : (
          <XCircle size={48} color="#ef4444" />
        )}
        <h3 style={{ marginTop: 12, fontSize: '1.1rem' }}>
          {result.status === 'SUCCESS' && '✅ Import Complete'}
          {result.status === 'PARTIAL' && '⚠️ Partial Import'}
          {result.status === 'FAILED'  && '❌ Import Failed'}
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
          {result.saved} saved · {result.failed} failed
        </p>
      </div>
      {result.results && result.results.map((r, i) => (
        <div key={i} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '10px 14px',
          background: r.status === 'SAVED' ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)',
          border: `1px solid ${r.status === 'SAVED' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
          borderRadius: 10, fontSize: '0.82rem'
        }}>
          <div>
            <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{r.description}</span>
            {r.error && <span style={{ color: '#f87171', marginLeft: 8 }}>— {r.error}</span>}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ color: r.type === 'INCOME' ? '#34d399' : '#f87171', fontWeight: 600 }}>
              {r.type === 'INCOME' ? '+' : '-'}{sym}{fmt(r.amount)}
            </span>
            {r.status === 'SAVED' ? (
              <CheckCircle2 size={14} color="#10b981" />
            ) : (
              <XCircle size={14} color="#ef4444" />
            )}
          </div>
        </div>
      ))}
      <button className="btn-secondary" onClick={onReset} style={{ alignSelf: 'center', marginTop: 8 }}>
        <RefreshCw size={14} /> Import More
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main ImportManager component
// ---------------------------------------------------------------------------

export default function ImportManager({ onImportComplete }) {
  const [mode,      setMode]      = useState('csv'); // 'csv' | 'image'
  const [step,      setStep]      = useState(0);     // 0=upload, 1=preview, 2=confirm, 3=done
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);

  // CSV state
  const [parseResult, setParseResult] = useState(null);
  const [rows,        setRows]        = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [editingId,   setEditingId]   = useState(null);

  // Image state
  const [imageResult,   setImageResult]   = useState(null);
  const [showImageForm, setShowImageForm] = useState(false);

  // Confirm result
  const [confirmResult, setConfirmResult] = useState(null);

  // Warnings & errors panels
  const [showErrors,   setShowErrors]   = useState(false);
  const [showWarnings, setShowWarnings] = useState(false);

  const reset = () => {
    setStep(0); setLoading(false); setError(null);
    setParseResult(null); setRows([]); setSelectedIds(new Set()); setEditingId(null);
    setImageResult(null); setShowImageForm(false); setConfirmResult(null);
  };

  // -------------------------------------------------------------------------
  // CSV upload handler
  // -------------------------------------------------------------------------
  const handleCsvFile = async (file) => {
    setError(null);
    setLoading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      const resp = await fetch('/api/import/csv', { method: 'POST', body, credentials: 'include' });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Upload failed');

      // Add stable _id to each row for selection tracking
      const tagged = data.valid_rows.map((r, i) => ({ ...r, _id: `row_${i}` }));
      setParseResult(data);
      setRows(tagged);
      // Pre-select all rows except confirmed duplicates
      setSelectedIds(new Set(tagged.filter(r => r.duplicate_status !== 'CONFIRMED_DUPLICATE').map(r => r._id)));
      setStep(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Image upload handler
  // -------------------------------------------------------------------------
  const handleImageFile = async (file) => {
    setError(null);
    setLoading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      const resp = await fetch('/api/import/image', { method: 'POST', body, credentials: 'include' });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Upload failed');
      setImageResult(data);
      setShowImageForm(true);
      setStep(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Confirm import
  // -------------------------------------------------------------------------
  const handleConfirm = async () => {
    const toImport = rows.filter(r => selectedIds.has(r._id));
    if (toImport.length === 0) { setError('No rows selected for import.'); return; }
    setLoading(true); setError(null);
    try {
      const body = {
        rows: toImport.map(r => ({
          date:        r.date,
          description: r.description,
          amount:      r.amount,
          type:        r.type,
          category:    r.category || 'General',
          source_ref:  r.source_ref || null,
          source_type: r.source_type || 'csv',
        })),
      };
      const resp = await fetch('/api/import/confirm', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body), credentials: 'include',
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Confirm failed');
      setConfirmResult(data);
      setStep(3);
      if (onImportComplete) onImportComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Single image confirm
  const handleImageSave = async (formData) => {
    setLoading(true); setError(null);
    try {
      const resp = await fetch('/api/import/confirm', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          rows: [{
            date:        formData.date,
            description: formData.description,
            amount:      parseFloat(formData.amount),
            type:        formData.type,
            category:    formData.category || 'General',
            source_ref:  imageResult?.extraction?.source_ref || null,
            source_type: 'image',
          }],
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Import failed');
      setConfirmResult(data); setStep(3);
      if (onImportComplete) onImportComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Row editing helpers
  // -------------------------------------------------------------------------
  const handleEdit = (id) => setEditingId(id);
  const handleSaveEdit = (updated) => {
    setRows(prev => prev.map(r => r._id === updated._id ? updated : r));
    setEditingId(null);
  };

  const toggleRow    = (id)    => setSelectedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleAll    = (state) => setSelectedIds(new Set(state ? rows.filter(r => r.duplicate_status !== 'CONFIRMED_DUPLICATE').map(r => r._id) : []));

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  const stats = parseResult?.stats;

  return (
    <div className="glass-card" style={{ marginTop: 28 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
        <div style={{ padding: 8, background: 'rgba(99,102,241,0.15)', borderRadius: 8, color: '#818cf8' }}>
          <Upload size={18} />
        </div>
        <div>
          <h3 style={{ fontSize: '1.12rem', color: 'var(--text-main)' }}>Import Transactions</h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Upload a bank statement CSV or a receipt / UPI screenshot
          </p>
        </div>
      </div>

      <Steps current={step} />

      {/* ── STEP 0: UPLOAD ── */}
      {step === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Mode selector */}
          <div style={{ display: 'flex', gap: 8 }}>
            {[['csv', FileText, 'CSV Bank Statement'], ['image', Image, 'Receipt / Screenshot']].map(([m, Icon, label]) => (
              <button key={m} onClick={() => { setMode(m); setError(null); }}
                style={{
                  flex: 1, padding: '10px 16px', borderRadius: 10, border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center',
                  fontWeight: 600, fontSize: '0.85rem', transition: 'all 0.2s',
                  background: mode === m ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                  color: mode === m ? '#c7d2fe' : 'var(--text-muted)',
                  boxShadow: mode === m ? '0 0 0 1px rgba(99,102,241,0.4)' : '0 0 0 1px rgba(255,255,255,0.07)',
                }}>
                <Icon size={16} /> {label}
              </button>
            ))}
          </div>

          <DropZone mode={mode} onFile={mode === 'csv' ? handleCsvFile : handleImageFile} disabled={loading} />

          {loading && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center' }}>
              <Spinner /> Uploading and parsing…
            </div>
          )}
          {error && <Alert type="error">{error}</Alert>}
        </div>
      )}

      {/* ── STEP 1: PREVIEW (CSV) ── */}
      {step === 1 && mode === 'csv' && parseResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Stats bar */}
          <div style={{
            display: 'flex', gap: 12, flexWrap: 'wrap',
            background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: '10px 14px',
            border: '1px solid var(--border-subtle)', fontSize: '0.8rem'
          }}>
            <span>📄 <strong>{stats.total_rows}</strong> rows read</span>
            <span>✅ <strong style={{ color: '#34d399' }}>{stats.valid}</strong> valid</span>
            {stats.parse_errors > 0  && <span>❌ <strong style={{ color: '#f87171' }}>{stats.parse_errors}</strong> parse errors</span>}
            {stats.invalid > 0       && <span>⚠️ <strong style={{ color: '#fbbf24' }}>{stats.invalid}</strong> invalid</span>}
            {stats.possible_duplicates > 0 && <span>🔁 <strong style={{ color: '#fbbf24' }}>{stats.possible_duplicates}</strong> possible duplicates</span>}
            {stats.confirmed_duplicates > 0 && <span>🚫 <strong style={{ color: '#f87171' }}>{stats.confirmed_duplicates}</strong> already imported</span>}
          </div>

          {/* Warnings collapsible */}
          {parseResult.warnings && parseResult.warnings.length > 0 && (
            <div>
              <button onClick={() => setShowWarnings(v => !v)}
                style={{ background: 'none', border: 'none', color: '#fbbf24', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', fontWeight: 600 }}>
                <AlertTriangle size={14} /> {parseResult.warnings.length} warning{parseResult.warnings.length > 1 ? 's' : ''}
                {showWarnings ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>
              {showWarnings && (
                <div style={{ marginTop: 6 }}>
                  <Alert type="warning">{parseResult.warnings.map((w, i) => <div key={i}>• {w}</div>)}</Alert>
                </div>
              )}
            </div>
          )}

          {/* Invalid / parse error rows collapsible */}
          {(parseResult.parse_errors?.length > 0 || parseResult.invalid_rows?.length > 0) && (
            <div>
              <button onClick={() => setShowErrors(v => !v)}
                style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', fontWeight: 600 }}>
                <XCircle size={14} /> {(parseResult.parse_errors?.length || 0) + (parseResult.invalid_rows?.length || 0)} skipped rows
                {showErrors ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>
              {showErrors && (
                <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {[...(parseResult.parse_errors || []), ...(parseResult.invalid_rows || [])].map((e, i) => (
                    <Alert key={i} type="error">{e.error || JSON.stringify(e)}</Alert>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Ambiguous mapping notice */}
          {parseResult.ambiguous && (
            <Alert type="warning">
              The column mapping is ambiguous. Please review the detected layout above and verify the preview below is correct.
              If columns are wrong, re-upload with a corrected file.
            </Alert>
          )}

          {/* Row editor */}
          {editingId && (
            <RowEditor
              row={rows.find(r => r._id === editingId)}
              onSave={handleSaveEdit}
              onCancel={() => setEditingId(null)}
            />
          )}

          {/* Preview table */}
          {rows.length > 0 ? (
            <PreviewTable
              rows={rows}
              selectedIds={selectedIds}
              onToggle={toggleRow}
              onToggleAll={toggleAll}
              onEdit={handleEdit}
            />
          ) : (
            <Alert type="warning">No valid rows were found after parsing and validation.</Alert>
          )}

          {error && <Alert type="error">{error}</Alert>}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 8, borderTop: '1px solid var(--border-subtle)' }}>
            <button className="btn-secondary" onClick={reset} style={{ fontSize: '0.82rem' }}>← Back</button>
            <button className="btn-primary"
              disabled={selectedIds.size === 0 || loading}
              onClick={handleConfirm}
              style={{ fontSize: '0.82rem' }}>
              {loading ? <><Spinner /> Importing…</> : <><Send size={14} /> Import {selectedIds.size} Transaction{selectedIds.size !== 1 ? 's' : ''}</>}
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 1: PREVIEW (Image) ── */}
      {step === 1 && mode === 'image' && imageResult && showImageForm && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Alert type={imageResult.requires_review ? 'warning' : 'info'}>
            {imageResult.requires_review
              ? 'Review required — extraction confidence is not high or transaction status is unclear. Verify all fields before importing.'
              : 'Fields extracted with high confidence. Please verify before importing.'}
          </Alert>
          <ImageReviewForm
            extraction={imageResult.extraction}
            onSave={handleImageSave}
            onCancel={reset}
          />
          {loading && <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}><Spinner /> Saving…</div>}
          {error && <Alert type="error">{error}</Alert>}
        </div>
      )}

      {/* ── STEP 3: DONE ── */}
      {step === 3 && confirmResult && (
        <ResultSummary result={confirmResult} onReset={reset} />
      )}

      {/* Inline spin animation */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

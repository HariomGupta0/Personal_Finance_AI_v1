import React, { useState } from 'react';
import { 
  Receipt, 
  Plus, 
  Trash2, 
  Sparkles, 
  ArrowUpRight, 
  ArrowDownRight, 
  Search, 
  Filter 
} from 'lucide-react';

export default function TransactionManager({ transactions, onAddTransaction, onDeleteTransaction }) {
  const [nlInput, setNlInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const sym = "₹";

  const handleNlSubmit = async (e) => {
    e.preventDefault();
    if (!nlInput.trim()) return;
    setIsSubmitting(true);
    try {
      await onAddTransaction({ natural_language_input: nlInput });
      setNlInput('');
    } catch (err) {
      alert("Failed to add transaction: " + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredTransactions = (transactions || []).filter(tx => {
    const matchesSearch = (tx.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (tx.category || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'ALL' || tx.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="glass-card" style={{ marginTop: '28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '8px', background: 'rgba(16, 185, 129, 0.15)', borderRadius: '8px', color: 'var(--accent-success)' }}>
            <Receipt size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--text-main)' }}>Transaction Ledger</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Real-time graph transactions & live balance updates</p>
          </div>
        </div>

        {/* Search & Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-dim)' }} />
            <input 
              type="text" 
              placeholder="Search description..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '6px 12px 6px 30px',
                color: 'var(--text-main)',
                fontSize: '0.82rem',
                outline: 'none'
              }}
            />
          </div>
        </div>
      </div>

      {/* Natural Language Quick Ingestion Bar */}
      <form onSubmit={handleNlSubmit} style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
        background: 'rgba(99, 102, 241, 0.06)',
        border: '1px solid rgba(99, 102, 241, 0.2)',
        borderRadius: '12px',
        padding: '8px 12px',
        alignItems: 'center'
      }}>
        <Sparkles size={18} color="var(--accent-primary)" />
        <input 
          type="text"
          placeholder="Natural Language Add: 'I spent ₹3500 on groceries today' or 'Paid 1200 for electricity'..."
          value={nlInput}
          onChange={(e) => setNlInput(e.target.value)}
          disabled={isSubmitting}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: 'var(--text-main)',
            fontSize: '0.88rem',
            outline: 'none'
          }}
        />
        <button type="submit" className="btn-primary" disabled={isSubmitting} style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
          {isSubmitting ? 'Ingesting...' : 'Ingest to Graph'}
        </button>
      </form>

      {/* Transaction Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.86rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.78rem', textTransform: 'uppercase' }}>
              <th style={{ padding: '10px 12px' }}>Type</th>
              <th style={{ padding: '10px 12px' }}>Description</th>
              <th style={{ padding: '10px 12px' }}>Category</th>
              <th style={{ padding: '10px 12px' }}>Date</th>
              <th style={{ padding: '10px 12px', textAlign: 'right' }}>Amount</th>
              <th style={{ padding: '10px 12px', textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)' }}>
                  No transactions found.
                </td>
              </tr>
            ) : (
              filteredTransactions.map((tx) => {
                const isExpense = tx.type === 'EXPENSE';
                return (
                  <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.15s ease' }}>
                    <td style={{ padding: '12px' }}>
                      <span className={`badge ${isExpense ? 'badge-danger' : 'badge-success'}`}>
                        {isExpense ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}
                        {tx.type}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-main)', fontWeight: '500' }}>
                      {tx.description}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span className="badge badge-info">{tx.category || 'General'}</span>
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-muted)' }}>
                      {tx.date}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right', fontWeight: '600', color: isExpense ? '#f87171' : '#34d399' }}>
                      {isExpense ? '-' : '+'}{sym}{parseFloat(tx.amount).toLocaleString()}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button 
                        onClick={() => onDeleteTransaction(tx.id)}
                        title="Delete transaction and restore balance"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-dim)',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: '6px',
                          transition: 'color 0.2s ease'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.color = '#ef4444'}
                        onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-dim)'}
                      >
                        <Trash2 size={15} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

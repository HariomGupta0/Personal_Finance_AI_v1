import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Bot,
  Send,
  Sparkles,
  CheckCircle,
  FileText,
  Database,
  Target,
  BarChart3,
  Lightbulb,
  Rocket,
  Zap,
  RotateCcw,
  ShieldCheck,
  AlertTriangle,
  Calendar,
  Clock,
  Code2
} from 'lucide-react';

const SUGGESTIONS = [
  "Can I spend ₹15000 on a phone?",
  "What is my savings rate?",
  "How much emergency fund do I need?",
  "How many months can I survive on my runway?",
  "Where did I spend the most?",
  "Give me a financial summary",
  "How much debt do I have?"
];

function parseAssistantSections(text) {
  if (!text) return null;

  // Check if standard structured sections are present
  const quickTakeMatch = text.match(/(?:🎯|\*\*🎯)?\s*(?:\*\*)?The Quick Take(?:\*\*)?:?\s*\n([\s\S]*?)(?=(?:📊|\*\*📊|\n\s*(?:\*\*)?The Numbers|\n\s*(?:\*\*)?Key Numbers|\n\s*(?:\*\*)?💡|\n\s*(?:\*\*)?🚀|$))/i);
  const numbersMatch = text.match(/(?:📊|\*\*📊)?\s*(?:\*\*)?(?:The Numbers|Key Numbers)(?:\*\*)?:?\s*\n([\s\S]*?)(?=(?:💡|\*\*💡|\n\s*(?:\*\*)?Smart Insights|\n\s*(?:\*\*)?🚀|$))/i);
  const insightsMatch = text.match(/(?:💡|\*\*💡)?\s*(?:\*\*)?Smart Insights(?:\*\*)?:?\s*\n([\s\S]*?)(?=(?:🚀|\*\*🚀|\n\s*(?:\*\*)?What You Should Do Next|\n\s*(?:\*\*)?Next Steps|$))/i);
  const actionsMatch = text.match(/(?:🚀|\*\*🚀)?\s*(?:\*\*)?(?:What You Should Do Next|Next Steps)(?:\*\*)?:?\s*\n([\s\S]*?)$/i);

  if (!quickTakeMatch && !numbersMatch && !insightsMatch && !actionsMatch) {
    return null;
  }

  return {
    quickTake: quickTakeMatch ? quickTakeMatch[1].trim() : null,
    numbers: numbersMatch ? numbersMatch[1].trim() : null,
    insights: insightsMatch ? insightsMatch[1].trim() : null,
    actions: actionsMatch ? actionsMatch[1].trim() : null
  };
}

function FormattedAssistantMessage({ text }) {
  const sections = parseAssistantSections(text);

  if (!sections) {
    return (
      <div className="ai-md-body">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="ai-bubble-container">
      {/* 1. Quick Take Card */}
      {sections.quickTake && (
        <div className="ai-card-quicktake">
          <div className="ai-card-quicktake-header">
            <Target size={15} /> The Quick Take
          </div>
          <div className="ai-card-quicktake-content ai-md-body">
            <ReactMarkdown>{sections.quickTake}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* 2. Key Numbers Card */}
      {sections.numbers && (
        <div className="ai-card-numbers">
          <div className="ai-card-numbers-header">
            <BarChart3 size={15} /> Key Breakdown
          </div>
          <div className="ai-md-body">
            <ReactMarkdown>{sections.numbers}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* 3. Smart Insights Card */}
      {sections.insights && (
        <div className="ai-card-insights">
          <div className="ai-card-insights-header">
            <Lightbulb size={15} /> Smart Insights
          </div>
          <div className="ai-md-body">
            <ReactMarkdown>{sections.insights}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* 4. Action Plan Card */}
      {sections.actions && (
        <div className="ai-card-actions">
          <div className="ai-card-actions-header">
            <Rocket size={15} /> Action Plan
          </div>
          <div className="ai-md-body">
            <ReactMarkdown>{sections.actions}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AssistantChat() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello Rahul! I am your explainable personal finance AI advisor powered by Dynamic Knowledge Graphs and GraphRAG. Ask me anything about purchase affordability, savings rate, emergency runway, or debt obligations.',
      evidence: [],
      math_result: null
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleClearHistory = async () => {
    try {
      await fetch('/api/assistant/clear-history', { method: 'POST' });
    } catch {
      // ignore
    }
    setMessages([
      {
        role: 'assistant',
        text: 'Hello Rahul! Conversation history has been reset. What would you like to analyze next?',
        evidence: [],
        math_result: null
      }
    ]);
  };

  const handleSend = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage = { role: 'user', text: textToSend };
    setMessages(prev => [...prev, userMessage]);
    if (!queryText) setInput('');
    setLoading(true);

    const historyPayload = messages
      .filter(m => m.text && !m.text.startsWith('Error connecting'))
      .slice(-4)
      .map(m => ({ role: m.role, content: (m.text || '').slice(0, 4000) }));

    try {
      const res = await fetch('/api/assistant/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: textToSend, history: historyPayload })
      });
      const data = await res.json();
      if (!res.ok) {
        let errorMsg = 'Unable to analyse this question';
        if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map(d => d.msg || (typeof d === 'string' ? d : JSON.stringify(d))).join(', ');
        } else if (data.detail && typeof data.detail === 'object') {
          errorMsg = data.detail.message || JSON.stringify(data.detail);
        }
        throw new Error(errorMsg);
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: data.explanation || 'Analysis complete.',
          evidence: data.evidence || [],
          evidence_metadata: data.evidence_metadata,
          source_identifiers: data.source_identifiers,
          graph_paths: data.graph_paths,
          math_result: data.math_result,
          intent: data.intent,
          latency_breakdown: data.latency_breakdown,
          tokens: data.tokens
        }
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: `Error connecting to AI Assistant: ${err.message || 'Unknown network error'}`,
          evidence: [],
          math_result: null
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '640px', padding: '0', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(255, 255, 255, 0.02)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '8px', background: 'rgba(99, 102, 241, 0.2)', borderRadius: '10px', color: 'var(--accent-primary)' }}>
            <Bot size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', color: 'var(--text-main)' }}>Financial AI Advisor</h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>GraphRAG Grounded • Deterministic Engine</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleClearHistory}
            title="Reset conversation context"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              background: 'rgba(255, 255, 255, 0.04)',
              color: 'var(--text-muted)',
              fontSize: '0.72rem',
              cursor: 'pointer'
            }}
          >
            <RotateCcw size={11} /> Clear Thread
          </button>
          <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
            <Database size={11} /> Neo4j Connected
          </span>
        </div>
      </div>

      {/* Message Stream */}
      <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className="animate-fade-in"
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: msg.role === 'user' ? '75%' : '95%',
              width: msg.role === 'assistant' && msg.evidence ? '95%' : 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            {msg.role === 'user' ? (
              <div style={{
                padding: '12px 18px',
                borderRadius: '16px 16px 4px 16px',
                background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                color: '#ffffff',
                fontSize: '0.92rem',
                lineHeight: '1.5',
                fontWeight: '500'
              }}>
                {msg.text}
              </div>
            ) : (
              <div style={{
                padding: '16px',
                borderRadius: '16px 16px 16px 4px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                width: '100%'
              }}>
                <FormattedAssistantMessage text={msg.text} />
              </div>
            )}

            {/* Grounded Evidence Presentation (Deterministic Financial Engine) */}
            {msg.role === 'assistant' && msg.evidence && msg.evidence.length > 0 && (
              <div style={{
                background: 'rgba(15, 23, 42, 0.9)',
                border: '1px solid rgba(99, 102, 241, 0.35)',
                borderRadius: '12px',
                padding: '14px 16px',
                marginTop: '6px',
                fontSize: '0.82rem',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
              }}>
                {/* Header: Verified Math Badge, Reporting Period & Data Freshness */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                  marginBottom: '10px',
                  paddingBottom: '8px',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontWeight: '600' }}>
                    <ShieldCheck size={15} />
                    <span>Deterministic Financial Evidence</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    {msg.evidence_metadata?.reporting_period && (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        background: 'rgba(99, 102, 241, 0.15)',
                        color: 'var(--accent-secondary)',
                        fontSize: '0.70rem',
                        fontWeight: '500'
                      }}>
                        <Calendar size={11} /> Period: {msg.evidence_metadata.reporting_period}
                      </span>
                    )}
                    {msg.evidence_metadata?.data_freshness && (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: 'var(--text-muted)',
                        fontSize: '0.70rem'
                      }}>
                        <Clock size={11} /> {msg.evidence_metadata.data_freshness}
                      </span>
                    )}
                  </div>
                </div>

                {/* Missing Data Caveat Alerts */}
                {msg.evidence_metadata?.caveats && msg.evidence_metadata.caveats.length > 0 && (
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    marginBottom: '10px',
                    padding: '8px 12px',
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.25)',
                    borderRadius: '8px'
                  }}>
                    {msg.evidence_metadata.caveats.map((cav, cIdx) => (
                      <div key={cIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', color: '#fbbf24', fontSize: '0.74rem', lineHeight: '1.4' }}>
                        <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <span><strong>Data Caveat:</strong> {cav}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Authoritative Metric Cards Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '8px' }}>
                  {msg.evidence.map((ev, eIdx) => (
                    <div key={eIdx} style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between'
                    }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '4px' }}>
                          <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem', fontWeight: '500' }}>{ev.label}</span>
                          <span style={{
                            color: 'var(--accent-primary)',
                            fontSize: '0.64rem',
                            padding: '1px 5px',
                            background: 'rgba(99, 102, 241, 0.12)',
                            borderRadius: '4px',
                            whiteSpace: 'nowrap'
                          }}>
                            {ev.source}
                          </span>
                        </div>
                        {/* Authoritative figure rendered directly from structured backend fields */}
                        <div style={{
                          color: '#ffffff',
                          fontWeight: '700',
                          fontSize: '0.98rem',
                          marginTop: '4px',
                          letterSpacing: '0.2px'
                        }}>
                          {ev.value}
                        </div>
                      </div>

                      <div style={{ marginTop: '6px' }}>
                        {ev.formula && (
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.66rem', fontStyle: 'italic', marginBottom: '4px' }}>
                            {ev.formula}
                          </div>
                        )}
                        {ev.source_node_ids && ev.source_node_ids.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px', marginTop: '2px' }}>
                            {ev.source_node_ids.slice(0, 3).map((nodeId, nIdx) => (
                              <span key={nIdx} style={{
                                fontSize: '0.62rem',
                                color: '#94a3b8',
                                background: 'rgba(0, 0, 0, 0.3)',
                                border: '1px solid rgba(255, 255, 255, 0.08)',
                                borderRadius: '4px',
                                padding: '1px 5px',
                                fontFamily: 'monospace'
                              }}>
                                {nodeId}
                              </span>
                            ))}
                            {ev.source_node_ids.length > 3 && (
                              <span style={{ fontSize: '0.62rem', color: '#94a3b8', padding: '1px 3px' }}>
                                +{ev.source_node_ids.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Calculation Methodology / Formula Footer */}
                {msg.evidence_metadata?.methodology_formula && (
                  <div style={{
                    marginTop: '10px',
                    paddingTop: '8px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: 'var(--text-muted)',
                    fontSize: '0.70rem'
                  }}>
                    <Code2 size={12} color="var(--accent-secondary)" style={{ flexShrink: 0 }} />
                    <span style={{ fontFamily: 'monospace' }}>
                      <strong>Formula:</strong> {msg.evidence_metadata.methodology_formula}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Telemetry & Latency Breakdown Badge */}
            {msg.role === 'assistant' && msg.latency_breakdown && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
                fontSize: '0.71rem',
                color: 'var(--text-muted)',
                padding: '4px 10px',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                width: 'fit-content',
                marginTop: '2px'
              }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', color: '#10b981', fontWeight: '600' }}>
                  <Zap size={11} /> {msg.latency_breakdown.total_ms}ms
                </span>
                <span>•</span>
                <span>Graph: {msg.latency_breakdown.graph_ms}ms</span>
                <span>•</span>
                <span>Engine: {msg.latency_breakdown.engine_ms}ms</span>
                <span>•</span>
                <span>LLM: {msg.latency_breakdown.llm_ms}ms</span>
                {msg.tokens && msg.tokens.total > 0 && (
                  <>
                    <span>•</span>
                    <span style={{ color: 'var(--accent-primary)', fontWeight: '500' }}>
                      {msg.tokens.total} tokens
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Sparkles size={16} color="var(--accent-primary)" className="glow-pulse" />
            Analyzing graph context & computing mathematical evidence...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Suggested Questions Chips */}
      <div style={{ padding: '8px 16px', display: 'flex', gap: '8px', overflowX: 'auto', borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)' }}>
        {SUGGESTIONS.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(chip)}
            disabled={loading}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              padding: '4px 10px',
              borderRadius: '999px',
              whiteSpace: 'nowrap',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)';
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
              e.currentTarget.style.color = 'var(--text-muted)';
            }}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} style={{
        padding: '14px 16px',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        gap: '10px',
        background: 'rgba(17, 24, 39, 0.95)'
      }}>
        <input
          type="text"
          placeholder="Ask a financial question (e.g. 'Can I spend ₹15,000 on a phone?')..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          style={{
            flex: 1,
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '10px 14px',
            color: 'var(--text-main)',
            fontSize: '0.9rem',
            outline: 'none'
          }}
        />
        <button type="submit" className="btn-primary" disabled={loading || !input.trim()} style={{ padding: '10px 18px' }}>
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}

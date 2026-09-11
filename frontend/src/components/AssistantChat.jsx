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
  Rocket
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

  const handleSend = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage = { role: 'user', text: textToSend };
    setMessages(prev => [...prev, userMessage]);
    if (!queryText) setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/assistant/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: textToSend })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Unable to analyse this question');
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: data.explanation || 'Analysis complete.',
          evidence: data.evidence || [],
          math_result: data.math_result,
          intent: data.intent
        }
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: `Error connecting to AI Assistant: ${err.message}`,
          evidence: [],
          math_result: null
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '620px', padding: '0', overflow: 'hidden' }}>
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
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

            {/* Grounded Evidence Card (for Assistant responses with evidence) */}
            {msg.role === 'assistant' && msg.evidence && msg.evidence.length > 0 && (
              <div style={{
                background: 'rgba(17, 24, 39, 0.85)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: '12px',
                padding: '14px',
                marginTop: '4px',
                fontSize: '0.82rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-secondary)', fontWeight: '600', marginBottom: '8px' }}>
                  <FileText size={14} /> Grounded Evidence & Verification
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px' }}>
                  {msg.evidence.map((ev, eIdx) => (
                    <div key={eIdx} style={{ background: 'rgba(255,255,255,0.03)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>{ev.label}</div>
                      <div style={{ color: 'var(--text-main)', fontWeight: '600', fontSize: '0.88rem' }}>{ev.value}</div>
                      <div style={{ color: 'var(--accent-primary)', fontSize: '0.68rem', marginTop: '2px' }}>{ev.source}</div>
                    </div>
                  ))}
                </div>
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

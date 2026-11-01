import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Helper to load .env variables without external packages
function loadEnv() {
  const envPath = path.join(__dirname, '.env');
  if (fs.existsSync(envPath)) {
    const lines = fs.readFileSync(envPath, 'utf8').split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx !== -1) {
        const key = trimmed.slice(0, eqIdx).trim();
        const val = trimmed.slice(eqIdx + 1).trim();
        if (!process.env[key]) {
          process.env[key] = val;
        }
      }
    }
  }
}

loadEnv();

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const MODEL = process.env.AUDIT_MODEL || 'anthropic/claude-3.5-sonnet';

if (!OPENROUTER_API_KEY) {
  console.error('\x1b[31m[Error] OPENROUTER_API_KEY is not set.\x1b[0m');
  console.log('\nPlease set your OpenRouter API key in .env or pass it as an environment variable:');
  console.log('  In .env: OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx');
  console.log('  Or run:  $env:OPENROUTER_API_KEY="sk-or-v1-xxxx"; node audit_with_claude.mjs\n');
  process.exit(1);
}

// Key files to audit
const AUDIT_FILES = [
  'backend/main.py',
  'backend/config.py',
  'backend/app/database/neo4j_service.py',
  'backend/app/rag/graph_rag.py',
  'backend/app/services/llm_service.py',
  'backend/app/services/prompt_builder.py',
  'backend/app/services/image_extractor.py',
  'backend/app/services/merchant_normalizer.py',
  'backend/app/engine/financial_engine.py',
  'backend/tests/unit/test_security_audit.py',
  'backend/tests/unit/test_llm_reliability.py',
  'frontend/src/App.jsx',
  'PROJECT_CONTEXT.md'
];

function readCodebaseContext() {
  console.log('\x1b[34m[1/3] Gathering codebase context for Claude...\x1b[0m');
  let gathered = '# PROJECT AUDIT DOSSIER: Personal Finance AI (FYP)\n\n';

  for (const relPath of AUDIT_FILES) {
    const fullPath = path.join(__dirname, relPath);
    if (fs.existsSync(fullPath)) {
      try {
        const content = fs.readFileSync(fullPath, 'utf8');
        gathered += `\n---\n## FILE: ${relPath}\n\`\`\`\n${content}\n\`\`\`\n`;
        console.log(`  ✓ Loaded: ${relPath} (${(content.length / 1024).toFixed(1)} KB)`);
      } catch (err) {
        console.warn(`  ! Could not read ${relPath}: ${err.message}`);
      }
    } else {
      console.warn(`  - Skipping non-existent file: ${relPath}`);
    }
  }
  return gathered;
}

const AUDITOR_SYSTEM_PROMPT = `You are a Principal Software Architect, Senior Security Auditor, and Academic Reviewer specializing in Graph AI, Deterministic Financial Systems, and RAG architectures.

You are performing an exhaustive, rigorous, and constructive audit of an undergraduate Final Year Project (FYP): "Personal Finance AI Assistant" (Neo4j GraphRAG + FastAPI + Deterministic Financial Engine + Vite/React).

Your audit must cover:
1. **Executive Summary & Architecture Review**: Overall system design, separation of concerns (deterministic financial engine vs. LLM probabilistic layer), and Neo4j GraphRAG grounding.
2. **Security & Prompt Injection Defenses**: Assessment of session handling, Cypher injection defenses, prompt boundary enforcement, and data privacy.
3. **GraphRAG & Financial Integrity**: Review of schema design, currency precision (INR / ₹), data provenance, and fallback resilience when LLM is unavailable.
4. **Code Quality, Concurrency & Error Handling**: Async/await hygiene, transient error retries, edge cases, and unit test coverage.
5. **Academic / FYP Rubric Evaluation**: Technical novelty, strengths for viva/defense, potential gaps examiners might question, and recommendations.
6. **Prioritized Action Plan**: Ranked list of high, medium, and low priority improvements.

Provide actionable, detailed markdown output with code snippets where relevant.`;

async function runAudit() {
  const codebaseContext = readCodebaseContext();
  
  console.log(`\n\x1b[34m[2/3] Calling ${MODEL} via OpenRouter...\x1b[0m`);
  console.log('Sending payload to OpenRouter API (this may take 30-60 seconds for a deep review)...\n');

  const startTime = Date.now();

  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/PersonalFinanceAI',
        'X-Title': 'Personal Finance AI Auditor'
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: AUDITOR_SYSTEM_PROMPT },
          {
            role: 'user',
            content: `Please conduct a comprehensive audit of this repository based on the following files and architectural context:\n\n${codebaseContext}`
          }
        ],
        temperature: 0.2,
        max_tokens: 4096
      })
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`OpenRouter API error (HTTP ${response.status}): ${errText}`);
    }

    const data = await response.json();
    const auditReport = data.choices?.[0]?.message?.content;
    const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);

    if (!auditReport) {
      throw new Error('Received empty response from OpenRouter.');
    }

    console.log(`\x1b[32m[3/3] Audit received in ${durationSec}s!\x1b[0m\n`);

    const outputPath = path.join(__dirname, 'CLAUDE_PROJECT_AUDIT.md');
    const fullOutput = `# Claude 3.5 Sonnet — Project Audit Report\n*Generated via OpenRouter on: ${new Date().toISOString()}*\n*Model:* \`${MODEL}\`\n\n${auditReport}`;
    
    fs.writeFileSync(outputPath, fullOutput, 'utf8');

    console.log(`\x1b[32m✔ Audit Report successfully written to:\x1b[0m ${outputPath}`);
    console.log('\nPreview of findings:\n-------------------');
    console.log(auditReport.slice(0, 1000) + '...\n\n[Full audit saved in CLAUDE_PROJECT_AUDIT.md]');
    
  } catch (err) {
    console.error('\x1b[31m[Audit Failed]\x1b[0m', err.message);
    process.exit(1);
  }
}

runAudit();

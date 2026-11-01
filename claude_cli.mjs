import readline from 'node:readline';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env
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
      if (!process.env[key]) process.env[key] = val;
    }
  }
}

const API_KEY = process.env.OPENROUTER_API_KEY;
const MODEL = process.env.CLAUDE_MODEL || 'anthropic/claude-3.5-sonnet';

if (!API_KEY) {
  console.error('\x1b[31m[Error] OPENROUTER_API_KEY is not set.\x1b[0m');
  console.log('Add it to your .env file: OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx\n');
  process.exit(1);
}

const messages = [
  {
    role: 'system',
    content: 'You are Claude 3.5 Sonnet, assisting the developer. Answer concisely and accurately. Format answers cleanly in markdown.'
  }
];

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('\x1b[36m====================================================\x1b[0m');
console.log(`\x1b[1m🤖 Claude 3.5 Sonnet (via OpenRouter)\x1b[0m`);
console.log(`Model: \x1b[33m${MODEL}\x1b[0m`);
console.log('Type your message and press Enter. (Type \x1b[31mexit\x1b[0m to quit)');
console.log('\x1b[36m====================================================\x1b[0m\n');

function promptUser() {
  rl.question('\x1b[32mYou:\x1b[0m ', async (userInput) => {
    const input = userInput.trim();
    if (!input) {
      promptUser();
      return;
    }
    if (input.toLowerCase() === 'exit' || input.toLowerCase() === 'quit') {
      console.log('\nGoodbye!');
      rl.close();
      return;
    }

    messages.push({ role: 'user', content: input });
    process.stdout.write('\n\x1b[35mClaude:\x1b[0m ');

    try {
      const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': 'http://localhost',
          'X-Title': 'Claude Interactive CLI'
        },
        body: JSON.stringify({
          model: MODEL,
          messages: messages,
          temperature: 0.3,
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`\x1b[31mError (${response.status}): ${errorText}\x1b[0m\n`);
      } else {
        const data = await response.json();
        const reply = data.choices?.[0]?.message?.content || '[No response]';
        console.log(reply + '\n');
        messages.push({ role: 'assistant', content: reply });
      }
    } catch (err) {
      console.error(`\x1b[31mNetwork error: ${err.message}\x1b[0m\n`);
    }

    promptUser();
  });
}

promptUser();

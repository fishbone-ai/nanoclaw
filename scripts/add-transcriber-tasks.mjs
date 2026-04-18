/**
 * One-time script: insert meeting-transcriber scheduled tasks into the NanoClaw DB.
 * Run with: node scripts/add-transcriber-tasks.mjs
 */
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';

const require = createRequire(import.meta.url);
const Database = require('better-sqlite3');

const DB_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'store', 'messages.db');
const db = new Database(DB_PATH);

// Use #meeting-transcription-logs channel group
const GROUP_FOLDER = 'slack_c0aljgpqsl8';
const CHAT_JID = 'slack:C0ALJGPQSL8';

const tasks = [
  {
    id: 'meeting-transcriber',
    group_folder: GROUP_FOLDER,
    chat_jid: CHAT_JID,
    prompt: `Run the meeting transcriber script:
\`\`\`bash
cd /workspace/global && python3 skills/meeting-transcriber/transcribe.py
\`\`\`
If the script outputs a NEW_TRANSCRIPTS section, process each listed transcript using the meeting-processor skill. Pass the exact path and owner hint as given.`,
    script: null,
    schedule_type: 'cron',
    schedule_value: '*/10 * * * *',
    context_mode: 'isolated',
    status: 'active',
    created_at: new Date().toISOString(),
  },
  {
    id: 'meeting-reconciler',
    group_folder: GROUP_FOLDER,
    chat_jid: CHAT_JID,
    prompt: `Run the meeting summary reconciler:
\`\`\`bash
cd /workspace/global && python3 skills/meeting-transcriber/reconcile.py
\`\`\`
If the script outputs a PENDING_TRANSCRIPTS section, process each listed transcript using the meeting-processor skill.`,
    script: null,
    schedule_type: 'cron',
    schedule_value: '*/15 * * * *',
    context_mode: 'isolated',
    status: 'active',
    created_at: new Date().toISOString(),
  },
];

// Compute next_run: next occurrence of the cron (just use now+1min for simplicity)
function nextRun() {
  const d = new Date();
  d.setMinutes(d.getMinutes() + 1, 0, 0);
  return d.toISOString();
}

const stmt = db.prepare(`
  INSERT OR REPLACE INTO scheduled_tasks
    (id, group_folder, chat_jid, prompt, script, schedule_type, schedule_value, context_mode, next_run, status, created_at)
  VALUES
    (@id, @group_folder, @chat_jid, @prompt, @script, @schedule_type, @schedule_value, @context_mode, @next_run, @status, @created_at)
`);

for (const task of tasks) {
  stmt.run({ ...task, next_run: nextRun() });
  console.log(`✓ Inserted task: ${task.id}`);
}

console.log('Done.');
db.close();

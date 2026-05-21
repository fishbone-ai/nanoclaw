# Slack Image Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a user sends an image in Slack, the bot downloads it, saves it to the group workspace, and embeds a file path in the message so the agent can use the `Read` tool to view it.

**Architecture:** Slack channel downloads the image (same auth pattern as audio), attaches base64 data to `NewMessage.imageAttachments`. The `onMessage` callback in `index.ts` calls a new helper `saveImageAttachments()` that writes the file to `groups/<folder>/images/` and appends the container-visible path to the message content. No changes to ContainerInput, container-runner, or agent-runner — the path is just part of the prompt string.

**Tech Stack:** Node.js built-in `fs`, `Buffer`; existing `@slack/bolt` client for auth; existing `readEnvFile` for bot token; vitest for tests.

---

## File Map

| File | Status | Role |
|------|--------|------|
| `src/types.ts` | Modify | Add `ImageAttachment` interface; add `imageAttachments?` to `NewMessage` |
| `src/channels/slack.ts` | Modify | Detect image files, download, attach base64 to outgoing `NewMessage` |
| `src/channels/slack.test.ts` | Modify | Add tests for image detection, download, and delivery |
| `src/image-attachments.ts` | Create | `saveImageAttachments(msg, groupFolder)` — writes files, appends paths to content |
| `src/image-attachments.test.ts` | Create | Unit tests for `saveImageAttachments` |
| `src/index.ts` | Modify | Call `saveImageAttachments` in `onMessage` before `storeMessage` |

---

## Task 1: Add `ImageAttachment` type to `NewMessage`

**Files:**
- Modify: `src/types.ts`

- [ ] **Step 1: Add `ImageAttachment` interface and field**

In `src/types.ts`, add the new interface above `NewMessage`, and add the optional field to `NewMessage`:

```typescript
export interface ImageAttachment {
  data: string;     // base64-encoded image bytes
  mimeType: string; // e.g. 'image/jpeg', 'image/png', 'image/gif', 'image/webp'
  filename?: string;
}
```

Then in `NewMessage`, add after `reply_to_sender_name`:
```typescript
  imageAttachments?: ImageAttachment[];
```

The final `NewMessage` interface in `src/types.ts` should look like:

```typescript
export interface NewMessage {
  id: string;
  chat_jid: string;
  sender: string;
  sender_name: string;
  content: string;
  timestamp: string;
  is_from_me?: boolean;
  is_bot_message?: boolean;
  thread_id?: string;
  reply_to_message_id?: string;
  reply_to_message_content?: string;
  reply_to_sender_name?: string;
  imageAttachments?: ImageAttachment[];
}
```

- [ ] **Step 2: Verify build is clean**

```bash
cd /share/nanoclaw && npm run build 2>&1 | tail -5
```

Expected: exits 0, no type errors.

- [ ] **Step 3: Commit**

```bash
git add src/types.ts
git commit -m "feat(types): add ImageAttachment to NewMessage"
```

---

## Task 2: Detect and download images in `slack.ts`

**Files:**
- Modify: `src/channels/slack.ts`
- Modify: `src/channels/slack.test.ts`

- [ ] **Step 1: Write failing tests**

At the end of the `describe('message handling', ...)` block in `src/channels/slack.test.ts`, add a new describe block. Also add `files.info` to the mock client (it's used when `url_private_download` is missing):

First, add `files: { info: vi.fn() }` to the `client` object inside the `vi.mock('@slack/bolt', ...)` block:

```typescript
client = {
  auth: {
    test: vi.fn().mockResolvedValue({ user_id: 'U_BOT_123' }),
  },
  chat: {
    postMessage: vi.fn().mockResolvedValue(undefined),
  },
  conversations: {
    list: vi.fn().mockResolvedValue({
      channels: [],
      response_metadata: {},
    }),
    replies: vi.fn().mockResolvedValue({ messages: [] }),
    info: vi.fn().mockResolvedValue({ channel: { name: 'test' } }),
  },
  files: {
    info: vi.fn().mockResolvedValue({ file: {} }),
  },
  users: {
    info: vi.fn().mockResolvedValue({
      user: { real_name: 'Alice Smith', name: 'alice' },
    }),
  },
  reactions: {
    add: vi.fn().mockResolvedValue(undefined),
    remove: vi.fn().mockResolvedValue(undefined),
  },
};
```

Then add this describe block after the existing `message handling` describe:

```typescript
describe('image handling', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches downloaded image to message', async () => {
    const imageBytes = Buffer.from('fake-png-data');
    vi.mocked(global.fetch as any).mockResolvedValue({
      ok: true,
      arrayBuffer: async () => imageBytes.buffer,
    });

    const opts = createTestOpts();
    const channel = new SlackChannel(opts);
    await channel.connect();

    await triggerMessageEvent({
      ...createMessageEvent({ text: undefined as any }),
      subtype: 'file_share',
      files: [
        {
          id: 'F123',
          mimetype: 'image/png',
          url_private_download: 'https://files.slack.com/img.png',
        },
      ],
    } as any);

    expect(opts.onMessage).toHaveBeenCalledWith(
      'slack:C0123456789',
      expect.objectContaining({
        imageAttachments: [
          expect.objectContaining({
            mimeType: 'image/png',
            data: imageBytes.toString('base64'),
          }),
        ],
      }),
    );
  });

  it('delivers image-only message with no text', async () => {
    const imageBytes = Buffer.from('fake-jpg-data');
    vi.mocked(global.fetch as any).mockResolvedValue({
      ok: true,
      arrayBuffer: async () => imageBytes.buffer,
    });

    const opts = createTestOpts();
    const channel = new SlackChannel(opts);
    await channel.connect();

    await triggerMessageEvent({
      ...createMessageEvent({ text: undefined as any }),
      subtype: 'file_share',
      files: [
        {
          id: 'F456',
          mimetype: 'image/jpeg',
          url_private_download: 'https://files.slack.com/img.jpg',
        },
      ],
    } as any);

    expect(opts.onMessage).toHaveBeenCalled();
  });

  it('appends failure note to content when image download fails', async () => {
    vi.mocked(global.fetch as any).mockResolvedValue({
      ok: false,
      status: 403,
    });

    const opts = createTestOpts();
    const channel = new SlackChannel(opts);
    await channel.connect();

    await triggerMessageEvent({
      ...createMessageEvent({ text: undefined as any }),
      subtype: 'file_share',
      files: [
        {
          id: 'F789',
          mimetype: 'image/jpeg',
          url_private_download: 'https://files.slack.com/fail.jpg',
        },
      ],
    } as any);

    expect(opts.onMessage).toHaveBeenCalledWith(
      'slack:C0123456789',
      expect.objectContaining({
        content: expect.stringContaining('[image attachment — download failed]'),
      }),
    );
  });

  it('handles multiple images in one message', async () => {
    const imageBytes = Buffer.from('img');
    vi.mocked(global.fetch as any).mockResolvedValue({
      ok: true,
      arrayBuffer: async () => imageBytes.buffer,
    });

    const opts = createTestOpts();
    const channel = new SlackChannel(opts);
    await channel.connect();

    await triggerMessageEvent({
      ...createMessageEvent({ text: 'Check these out' }),
      files: [
        { id: 'F1', mimetype: 'image/png', url_private_download: 'https://files.slack.com/a.png' },
        { id: 'F2', mimetype: 'image/jpeg', url_private_download: 'https://files.slack.com/b.jpg' },
      ],
    } as any);

    expect(opts.onMessage).toHaveBeenCalledWith(
      'slack:C0123456789',
      expect.objectContaining({
        imageAttachments: expect.arrayContaining([
          expect.objectContaining({ mimeType: 'image/png' }),
          expect.objectContaining({ mimeType: 'image/jpeg' }),
        ]),
      }),
    );
  });

  it('skips non-image files silently', async () => {
    const opts = createTestOpts();
    const channel = new SlackChannel(opts);
    await channel.connect();

    // PDF — not an image
    await triggerMessageEvent({
      ...createMessageEvent({ text: 'Here is a doc' }),
      files: [
        { id: 'F_PDF', mimetype: 'application/pdf', url_private_download: 'https://files.slack.com/doc.pdf' },
      ],
    } as any);

    expect(opts.onMessage).toHaveBeenCalledWith(
      'slack:C0123456789',
      expect.objectContaining({
        imageAttachments: undefined,
      }),
    );
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /share/nanoclaw && npx vitest run src/channels/slack.test.ts 2>&1 | tail -20
```

Expected: 5 new test failures (image handling tests not yet implemented).

- [ ] **Step 3: Implement image detection and download in `slack.ts`**

In `setupEventHandlers`, after the `audioFile` line (line ~105), add `imageFile` detection and fix the guard. Also add a download block after the audio block. The relevant section currently looks like:

```typescript
const audioFile = files?.find((f) => f.mimetype?.startsWith('audio/'));
if (!msg.text && !audioFile) return;
```

Replace with:

```typescript
const audioFile = files?.find((f) => f.mimetype?.startsWith('audio/'));
const imageFiles = files?.filter((f) => f.mimetype?.startsWith('image/')) ?? [];
if (!msg.text && !audioFile && imageFiles.length === 0) return;
```

Then, after the audio handling block (after the closing `}` of `if (audioFile && !isBotMessage)`), add:

```typescript
let downloadedImages: Array<{ data: string; mimeType: string; filename?: string }> = [];
if (imageFiles.length > 0 && !isBotMessage) {
  downloadedImages = await this.downloadImageFiles(imageFiles);
  // If all downloads failed and there's no text, note the failure in content
  if (downloadedImages.length === 0 && !content) {
    content = `[image attachment — download failed]`;
  }
}
```

Then, in the `opts.onMessage(jid, { ... })` call at the end, add `imageAttachments`:

```typescript
this.opts.onMessage(jid, {
  id: msg.ts,
  chat_jid: jid,
  sender: msg.user || msg.bot_id || '',
  sender_name: senderName,
  content,
  timestamp,
  is_from_me: isBotMessage,
  is_bot_message: isBotMessage,
  reply_to_message_id: isThreadReply ? threadTs : undefined,
  reply_to_message_content: replyToContent,
  reply_to_sender_name: replyToSenderName,
  imageAttachments: downloadedImages.length > 0 ? downloadedImages : undefined,
});
```

Finally, add the `downloadImageFiles` private method after `transcribeAudioFile`:

```typescript
private async downloadImageFiles(
  files: Array<{ id: string; mimetype?: string; url_private_download?: string; name?: string }>,
): Promise<Array<{ data: string; mimeType: string; filename?: string }>> {
  const env = readEnvFile(['SLACK_BOT_TOKEN']);
  const results: Array<{ data: string; mimeType: string; filename?: string }> = [];

  for (const file of files) {
    try {
      let downloadUrl = file.url_private_download;
      if (!downloadUrl) {
        const info = await this.app.client.files.info({ file: file.id });
        downloadUrl = (info.file as { url_private_download?: string })
          ?.url_private_download;
      }
      if (!downloadUrl) {
        logger.warn({ fileId: file.id }, 'Slack: no download URL for image');
        continue;
      }

      const resp = await fetch(downloadUrl, {
        headers: { Authorization: `Bearer ${env.SLACK_BOT_TOKEN}` },
      });
      if (!resp.ok) {
        logger.warn(
          { status: resp.status, fileId: file.id },
          'Slack: image download failed',
        );
        continue;
      }

      const buffer = await resp.arrayBuffer();
      const data = Buffer.from(buffer).toString('base64');
      results.push({
        data,
        mimeType: file.mimetype ?? 'image/jpeg',
        filename: (file as { name?: string }).name,
      });
      logger.info(
        { fileId: file.id, mimeType: file.mimetype, bytes: buffer.byteLength },
        'Slack: downloaded image',
      );
    } catch (err) {
      logger.warn({ err, fileId: file.id }, 'Slack: failed to download image');
    }
  }

  return results;
}
```

Also update the `SlackFileRef` type inside `setupEventHandlers` to include `name`:

```typescript
type SlackFileRef = {
  id: string;
  mimetype?: string;
  url_private_download?: string;
  name?: string;
};
```

- [ ] **Step 4: Run tests**

```bash
cd /share/nanoclaw && npx vitest run src/channels/slack.test.ts 2>&1 | tail -20
```

Expected: all tests pass, including the 5 new image handling tests.

- [ ] **Step 5: Build check**

```bash
npm run build 2>&1 | tail -5
```

Expected: exits 0, no errors.

- [ ] **Step 6: Commit**

```bash
git add src/channels/slack.ts src/channels/slack.test.ts
git commit -m "feat(slack): detect and download image attachments"
```

---

## Task 3: Save images to group folder and embed path in content

**Files:**
- Create: `src/image-attachments.ts`
- Create: `src/image-attachments.test.ts`
- Modify: `src/index.ts`

- [ ] **Step 1: Write failing tests**

Create `src/image-attachments.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';

vi.mock('./logger.js', () => ({
  logger: { info: vi.fn(), warn: vi.fn() },
}));

vi.mock('./group-folder.js', () => ({
  resolveGroupFolderPath: (folder: string) => `/tmp/test-groups/${folder}`,
}));

import { saveImageAttachments } from './image-attachments.js';
import { NewMessage } from './types.js';

function makeMsg(overrides: Partial<NewMessage> = {}): NewMessage {
  return {
    id: '1704067200.000100',
    chat_jid: 'slack:C123',
    sender: 'U123',
    sender_name: 'Alice',
    content: 'Hello',
    timestamp: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

describe('saveImageAttachments', () => {
  const tmpBase = '/tmp/test-groups';

  beforeEach(() => {
    fs.rmSync(tmpBase, { recursive: true, force: true });
  });

  it('does nothing when there are no attachments', () => {
    const msg = makeMsg();
    saveImageAttachments(msg, 'test-channel');
    expect(msg.content).toBe('Hello');
  });

  it('saves jpeg and appends container path to content', () => {
    const imageData = Buffer.from('fake-jpeg').toString('base64');
    const msg = makeMsg({
      imageAttachments: [{ data: imageData, mimeType: 'image/jpeg' }],
    });

    saveImageAttachments(msg, 'test-channel');

    const imagesDir = '/tmp/test-groups/test-channel/images';
    const files = fs.readdirSync(imagesDir);
    expect(files).toHaveLength(1);
    expect(files[0]).toMatch(/\.jpg$/);
    expect(fs.readFileSync(path.join(imagesDir, files[0]))).toEqual(
      Buffer.from('fake-jpeg'),
    );
    expect(msg.content).toContain('/workspace/group/images/');
    expect(msg.content).toContain('use Read to view it');
  });

  it('uses correct extension for each mime type', () => {
    for (const [mimeType, ext] of [
      ['image/jpeg', 'jpg'],
      ['image/jpg', 'jpg'],
      ['image/png', 'png'],
      ['image/gif', 'gif'],
      ['image/webp', 'webp'],
    ] as const) {
      fs.rmSync(tmpBase, { recursive: true, force: true });
      const msg = makeMsg({
        imageAttachments: [{ data: Buffer.from('x').toString('base64'), mimeType }],
      });
      saveImageAttachments(msg, 'test-channel');
      const files = fs.readdirSync('/tmp/test-groups/test-channel/images');
      expect(files[0]).toMatch(new RegExp(`\\.${ext}$`));
    }
  });

  it('saves multiple images and appends a path line for each', () => {
    const msg = makeMsg({
      imageAttachments: [
        { data: Buffer.from('a').toString('base64'), mimeType: 'image/png' },
        { data: Buffer.from('b').toString('base64'), mimeType: 'image/jpeg' },
      ],
    });

    saveImageAttachments(msg, 'test-channel');

    const files = fs.readdirSync('/tmp/test-groups/test-channel/images');
    expect(files).toHaveLength(2);
    const pathLines = msg.content.split('\n').filter((l) => l.startsWith('[Image at'));
    expect(pathLines).toHaveLength(2);
  });

  it('appends path to existing content', () => {
    const msg = makeMsg({
      content: 'Check this out',
      imageAttachments: [
        { data: Buffer.from('x').toString('base64'), mimeType: 'image/png' },
      ],
    });

    saveImageAttachments(msg, 'test-channel');

    expect(msg.content).toMatch(/^Check this out\n\[Image at/);
  });

  it('sets content to path when original content is empty', () => {
    const msg = makeMsg({
      content: '',
      imageAttachments: [
        { data: Buffer.from('x').toString('base64'), mimeType: 'image/png' },
      ],
    });

    saveImageAttachments(msg, 'test-channel');

    expect(msg.content).toMatch(/^\[Image at/);
  });

  it('clears imageAttachments after saving', () => {
    const msg = makeMsg({
      imageAttachments: [
        { data: Buffer.from('x').toString('base64'), mimeType: 'image/png' },
      ],
    });

    saveImageAttachments(msg, 'test-channel');

    expect(msg.imageAttachments).toBeUndefined();
  });

  it('uses dot-safe message id in filename (replaces . with -)', () => {
    const msg = makeMsg({
      id: '1704067200.000100',
      imageAttachments: [
        { data: Buffer.from('x').toString('base64'), mimeType: 'image/png' },
      ],
    });

    saveImageAttachments(msg, 'test-channel');

    const files = fs.readdirSync('/tmp/test-groups/test-channel/images');
    expect(files[0]).not.toContain('.');
    expect(files[0]).toContain('1704067200-000100');
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /share/nanoclaw && npx vitest run src/image-attachments.test.ts 2>&1 | tail -10
```

Expected: errors because `src/image-attachments.ts` doesn't exist yet.

- [ ] **Step 3: Create `src/image-attachments.ts`**

```typescript
import fs from 'fs';
import path from 'path';
import { resolveGroupFolderPath } from './group-folder.js';
import { logger } from './logger.js';
import { NewMessage } from './types.js';

const MIME_TO_EXT: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/jpg': 'jpg',
  'image/png': 'png',
  'image/gif': 'gif',
  'image/webp': 'webp',
};

export function saveImageAttachments(
  msg: NewMessage,
  groupFolder: string,
): void {
  if (!msg.imageAttachments?.length) return;

  const imagesDir = path.join(resolveGroupFolderPath(groupFolder), 'images');
  fs.mkdirSync(imagesDir, { recursive: true });

  for (let i = 0; i < msg.imageAttachments.length; i++) {
    const attachment = msg.imageAttachments[i];
    const ext = MIME_TO_EXT[attachment.mimeType] ?? 'bin';
    const safeId = msg.id.replace(/\./g, '-');
    const filename = `slack-image-${safeId}-${i}.${ext}`;
    const filepath = path.join(imagesDir, filename);

    try {
      fs.writeFileSync(filepath, Buffer.from(attachment.data, 'base64'));
      const containerPath = `/workspace/group/images/${filename}`;
      msg.content = msg.content
        ? `${msg.content}\n[Image at ${containerPath} — use Read to view it]`
        : `[Image at ${containerPath} — use Read to view it]`;
      logger.info({ filename }, 'Saved Slack image attachment');
    } catch (err) {
      logger.warn({ err, filename }, 'Failed to save Slack image attachment');
    }
  }

  msg.imageAttachments = undefined;
}
```

- [ ] **Step 4: Run tests**

```bash
cd /share/nanoclaw && npx vitest run src/image-attachments.test.ts 2>&1 | tail -20
```

Expected: all 8 tests pass.

- [ ] **Step 5: Call `saveImageAttachments` in `index.ts`**

In `src/index.ts`, add the import near the top (alongside other src imports):

```typescript
import { saveImageAttachments } from './image-attachments.js';
```

In the `onMessage` callback (around line 810), add the call between the sender-allowlist check and `storeMessage`:

```typescript
onMessage: (chatJid: string, msg: NewMessage) => {
  // Remote control commands — intercept before storage
  const trimmed = msg.content.trim();
  if (trimmed === '/remote-control' || trimmed === '/remote-control-end') {
    handleRemoteControl(trimmed, chatJid, msg).catch((err) =>
      logger.error({ err, chatJid }, 'Remote control command error'),
    );
    return;
  }

  // Sender allowlist drop mode: discard messages from denied senders before storing
  if (!msg.is_from_me && !msg.is_bot_message && registeredGroups[chatJid]) {
    const cfg = loadSenderAllowlist();
    if (
      shouldDropMessage(chatJid, cfg) &&
      !isSenderAllowed(chatJid, msg.sender, cfg)
    ) {
      if (cfg.logDenied) {
        logger.debug(
          { chatJid, sender: msg.sender },
          'sender-allowlist: dropping message (drop mode)',
        );
      }
      return;
    }
  }

  // Save image attachments to group workspace and embed container paths in content
  if (msg.imageAttachments?.length && registeredGroups[chatJid]?.folder) {
    saveImageAttachments(msg, registeredGroups[chatJid].folder);
  }

  storeMessage(msg);
},
```

- [ ] **Step 6: Build check**

```bash
npm run build 2>&1 | tail -5
```

Expected: exits 0, no errors.

- [ ] **Step 7: Run full test suite**

```bash
npx vitest run 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/image-attachments.ts src/image-attachments.test.ts src/index.ts
git commit -m "feat(slack): save image attachments to group workspace and embed path in prompt"
```

---

## Task 4: Rebuild and restart

- [ ] **Step 1: Rebuild nanoclaw**

```bash
npm run build 2>&1 | tail -5
```

Expected: exits 0.

- [ ] **Step 2: Restart the service**

```bash
systemctl --user restart nanoclaw 2>/dev/null || ha addon restart local_nanoclaw 2>/dev/null || echo "Please restart nanoclaw manually"
```

- [ ] **Step 3: Smoke-test**

Send an image to a registered Slack channel. The bot should:
1. Add an ⏳ reaction (typing indicator)
2. Reply in the thread referencing what the image shows
3. Leave a file at `groups/<folder>/images/slack-image-<ts>-0.<ext>` on the host

Verify the file exists:
```bash
ls -lh /share/nanoclaw/groups/*/images/ 2>/dev/null || echo "No images saved yet"
```

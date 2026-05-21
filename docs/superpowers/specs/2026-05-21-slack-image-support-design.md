# Slack Image Support Design

**Date:** 2026-05-21  
**Status:** Approved

## Problem

When users send images in Slack, the bot silently ignores them. The early-exit guard at line 106 of `src/channels/slack.ts` only passes messages through if they contain text or an audio file — images fall through and are never delivered to the agent.

## Approach: Image-as-file + Read tool

Download the image from Slack, save it to the group's workspace folder on the host, and embed a file path reference in the message content. The agent reads the file using the `Read` tool, which natively supports images in Claude Code.

The group folder is already mounted into the container at `/workspace/group/`. No container changes, no rebuild, no changes to `ContainerInput` or `agent-runner`.

## Data Flow

```
Slack event (file_share / files array)
  ↓
slack.ts: detect image mimetype, download with bot token auth
  ↓
NewMessage.imageAttachments = [{ data, mimeType, filename }]
  ↓
index.ts onMessage: save to groups/<folder>/images/slack-image-<ts>.ext
  ↓
msg.content += "\n[Image at /workspace/group/images/slack-image-<ts>.ext — use Read to view it]"
  ↓
storeMessage(msg)  ← only the path reference persists to DB; base64 is discarded
  ↓
agent receives path in prompt → calls Read → Claude sees the image
```

## Components

### `src/types.ts`

Add:

```typescript
export interface ImageAttachment {
  data: string;      // base64-encoded image bytes
  mimeType: string;  // e.g. 'image/jpeg', 'image/png', 'image/gif', 'image/webp'
  filename?: string; // original Slack filename, used to derive extension
}
```

Add `imageAttachments?: ImageAttachment[]` to `NewMessage`.

### `src/channels/slack.ts`

- In `setupEventHandlers`, alongside `audioFile`, find `imageFile` (first file where `mimetype` starts with `image/`)
- Fix the early-exit guard: pass the message through if there is text, an audio file, **or an image file**
- After audio handling, add an `imageFile` download block:
  - Fetch `url_private_download` with `Authorization: Bearer <SLACK_BOT_TOKEN>` (same as audio)
  - Base64-encode the response body
  - Set `msg.imageAttachments = [{ data, mimeType, filename }]` on the `NewMessage` object before calling `opts.onMessage`
- Support multiple images: if `files` has multiple images, attach all of them
- Log image details at `info` level (file ID, mimetype, size) for observability

### `src/index.ts`

In the `onMessage` callback, before `storeMessage(msg)`:

1. Check `msg.imageAttachments?.length`
2. Look up `registeredGroups[chatJid]?.folder`; if no registered group, skip (group may not be registered yet)
3. Resolve the save directory: `resolveGroupFolderPath(folder)/images/`; create it if it doesn't exist
4. For each attachment, derive an extension from `mimeType` (`image/jpeg` → `jpg`, `image/png` → `png`, `image/gif` → `gif`, `image/webp` → `webp`; fall back to `bin`)
5. Write the decoded bytes to `<saveDir>/slack-image-<msg.id>-<index>.<ext>`
6. Append to `msg.content`: `\n[Image at /workspace/group/images/slack-image-<msg.id>-<index>.<ext> — use Read to view it]`
7. Clear `msg.imageAttachments` before `storeMessage` (not persisted to DB)

## Error Handling

- Download failure → log a warning, skip the attachment (message still delivered with text if any)
- Write failure → log a warning, skip the path reference for that file
- Image-only message where download fails and there's no text → still deliver the message with content `@<ASSISTANT_NAME> [image attachment — download failed]` so the agent knows something was sent

## What Is Not Changing

- `ContainerInput` — still `prompt: string`
- `container-runner.ts` — no changes
- `agent-runner/src/index.ts` — no changes
- Container image — no rebuild needed
- Database schema — `imageAttachments` is never written to SQLite

## File Accumulation

Images are written to `groups/<folder>/images/` and are not automatically deleted. This is intentional — they become part of the group's persistent workspace, accessible to the agent for later reference. Users can clean them up manually or via agent tools.

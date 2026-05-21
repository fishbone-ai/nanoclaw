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
  try {
    fs.mkdirSync(imagesDir, { recursive: true });
  } catch (err) {
    logger.warn({ err, imagesDir }, 'Failed to create images directory');
    return;
  }

  const safeId = msg.id.replace(/\./g, '-');
  for (let i = 0; i < msg.imageAttachments.length; i++) {
    const attachment = msg.imageAttachments[i];
    const ext = MIME_TO_EXT[attachment.mimeType] ?? 'bin';
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

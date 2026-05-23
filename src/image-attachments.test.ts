import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

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
        imageAttachments: [
          { data: Buffer.from('x').toString('base64'), mimeType },
        ],
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
    const pathLines = msg.content
      .split('\n')
      .filter((l) => l.startsWith('[Image at'));
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
    expect(files[0]).not.toContain('1704067200.000100');
    expect(files[0]).toContain('1704067200-000100');
  });
});

import { App, LogLevel } from '@slack/bolt';
import type { GenericMessageEvent, BotMessageEvent } from '@slack/types';

import { ASSISTANT_NAME, TRIGGER_PATTERN } from '../config.js';
import { updateChatName } from '../db.js';
import { readEnvFile } from '../env.js';
import { logger } from '../logger.js';
import { registerChannel, ChannelOpts } from './registry.js';
import {
  Channel,
  OnInboundMessage,
  OnChatMetadata,
  RegisteredGroup,
} from '../types.js';

// Slack's chat.postMessage API limits text to ~4000 characters per call.
// Messages exceeding this are split into sequential chunks.
const MAX_MESSAGE_LENGTH = 4000;

// The message subtypes we process. Bolt delivers all subtypes via app.event('message');
// we filter to regular messages (GenericMessageEvent, subtype undefined) and bot messages
// (BotMessageEvent, subtype 'bot_message') so we can track our own output.
type HandledMessageEvent = GenericMessageEvent | BotMessageEvent;

export interface SlackChannelOpts {
  onMessage: OnInboundMessage;
  onChatMetadata: OnChatMetadata;
  registeredGroups: () => Record<string, RegisteredGroup>;
  registerGroup?: (jid: string, group: RegisteredGroup) => void;
}

export class SlackChannel implements Channel {
  name = 'slack';

  private app: App;
  private botUserId: string | undefined;
  private connected = false;
  private outgoingQueue: Array<{
    jid: string;
    text: string;
    replyToMessageId?: string;
  }> = [];
  private flushing = false;
  private userNameCache = new Map<string, string>();
  // Maps inbound message ts → thread root ts, so replies always land in the
  // correct thread regardless of interleaving. Keyed by msg.ts (not channel),
  // so replying to an older thread sends the response there, not to the latest.
  private replyThreadTs = new Map<string, string>();

  private opts: SlackChannelOpts;

  constructor(opts: SlackChannelOpts) {
    this.opts = opts;

    // Read tokens from .env (not process.env — keeps secrets off the environment
    // so they don't leak to child processes, matching NanoClaw's security pattern)
    const env = readEnvFile(['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']);
    const botToken = env.SLACK_BOT_TOKEN;
    const appToken = env.SLACK_APP_TOKEN;

    if (!botToken || !appToken) {
      throw new Error(
        'SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env',
      );
    }

    this.app = new App({
      token: botToken,
      appToken,
      socketMode: true,
      logLevel: LogLevel.ERROR,
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    // Use app.event('message') instead of app.message() to capture all
    // message subtypes including bot_message (needed to track our own output)
    this.app.event('message', async ({ event }) => {
      // Bolt's event type is the full MessageEvent union (17+ subtypes).
      // We filter on subtype first, then narrow to the two types we handle.
      const subtype = (event as { subtype?: string }).subtype;
      if (subtype && subtype !== 'bot_message') return;

      // After filtering, event is either GenericMessageEvent or BotMessageEvent
      const msg = event as HandledMessageEvent;

      if (!msg.text) return;

      const jid = `slack:${msg.channel}`;
      const timestamp = new Date(parseFloat(msg.ts) * 1000).toISOString();
      const isGroup = msg.channel_type !== 'im';

      // Always report metadata for group discovery
      this.opts.onChatMetadata(jid, timestamp, undefined, 'slack', isGroup);

      // Auto-register unknown chats on first interaction:
      //   - DMs: any message (they're inherently 1:1 with the bot).
      //   - Channels/groups: only when the bot is @-mentioned, so random
      //     workspace members can't accidentally onboard the bot by posting.
      let groups = this.opts.registeredGroups();
      if (!groups[jid] && this.opts.registerGroup) {
        const isMentioned =
          !!this.botUserId && msg.text.includes(`<@${this.botUserId}>`);
        if (!isGroup || isMentioned) {
          await this.autoRegister(jid, msg.channel, isGroup);
          groups = this.opts.registeredGroups();
        }
      }
      if (!groups[jid]) return;

      const isBotMessage = !!msg.bot_id || msg.user === this.botUserId;

      // Map this message's ts to its thread root so sendMessage can reply
      // deterministically to the correct thread, regardless of interleaving.
      if (!isBotMessage) {
        const threadRoot = (msg as { thread_ts?: string }).thread_ts || msg.ts;
        if (threadRoot) this.replyThreadTs.set(msg.ts, threadRoot);
      }

      let senderName: string;
      if (isBotMessage) {
        senderName = ASSISTANT_NAME;
      } else {
        senderName =
          (msg.user ? await this.resolveUserName(msg.user) : undefined) ||
          msg.user ||
          'unknown';
      }

      // Translate Slack <@UBOTID> mentions into TRIGGER_PATTERN format.
      // Slack encodes @mentions as <@U12345>, which won't match TRIGGER_PATTERN
      // (e.g., ^@<ASSISTANT_NAME>\b), so we prepend the trigger when the bot is @mentioned.
      let content = msg.text;
      if (this.botUserId && !isBotMessage) {
        const mentionPattern = `<@${this.botUserId}>`;
        if (
          content.includes(mentionPattern) &&
          !TRIGGER_PATTERN.test(content)
        ) {
          content = `@${ASSISTANT_NAME} ${content}`;
        }
      }

      // For thread replies, fetch the parent message so the agent has context
      // of what's being replied to (e.g. Ohav replying to the bot's task check).
      const threadTs = (msg as { thread_ts?: string }).thread_ts;
      const isThreadReply = !isBotMessage && threadTs && threadTs !== msg.ts;
      let replyToContent: string | undefined;
      let replyToSenderName: string | undefined;
      if (isThreadReply) {
        try {
          const replies = await this.app.client.conversations.replies({
            channel: msg.channel,
            ts: threadTs,
            limit: 1,
            inclusive: true,
          });
          const parent = replies.messages?.[0];
          if (parent?.text) {
            replyToContent = parent.text;
            replyToSenderName = parent.bot_id
              ? ASSISTANT_NAME
              : parent.user
                ? ((await this.resolveUserName(parent.user)) ?? parent.user)
                : ASSISTANT_NAME;
          }
        } catch (err) {
          logger.debug(
            { err, threadTs },
            'Slack: failed to fetch thread parent',
          );
        }
      }

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
      });
    });
  }

  async connect(): Promise<void> {
    await this.app.start();

    // Get bot's own user ID for self-message detection.
    // Resolve this BEFORE setting connected=true so that messages arriving
    // during startup can correctly detect bot-sent messages.
    try {
      const auth = await this.app.client.auth.test();
      this.botUserId = auth.user_id as string;
      logger.info({ botUserId: this.botUserId }, 'Connected to Slack');
    } catch (err) {
      logger.warn({ err }, 'Connected to Slack but failed to get bot user ID');
    }

    this.connected = true;

    // Promote already-registered channels to isMain if SLACK_IS_MAIN=true
    this.promoteSlackChannels();

    // Flush any messages queued before connection
    await this.flushOutgoingQueue();

    // Sync channel names on startup
    await this.syncChannelMetadata();
  }

  async sendMessage(
    jid: string,
    text: string,
    replyToMessageId?: string,
  ): Promise<void> {
    const channelId = jid.replace(/^slack:/, '');

    if (!this.connected) {
      this.outgoingQueue.push({ jid, text, replyToMessageId });
      logger.info(
        { jid, queueSize: this.outgoingQueue.length },
        'Slack disconnected, message queued',
      );
      return;
    }

    const threadTs = replyToMessageId
      ? this.replyThreadTs.get(replyToMessageId)
      : undefined;
    try {
      // Slack limits messages to ~4000 characters; split if needed.
      // Every chunk goes into the same thread so the reply reads as one.
      if (text.length <= MAX_MESSAGE_LENGTH) {
        await this.app.client.chat.postMessage({
          channel: channelId,
          text,
          thread_ts: threadTs,
        });
      } else {
        for (let i = 0; i < text.length; i += MAX_MESSAGE_LENGTH) {
          await this.app.client.chat.postMessage({
            channel: channelId,
            text: text.slice(i, i + MAX_MESSAGE_LENGTH),
            thread_ts: threadTs,
          });
        }
      }
      logger.info({ jid, length: text.length, threadTs }, 'Slack message sent');
    } catch (err) {
      this.outgoingQueue.push({ jid, text });
      logger.warn(
        { jid, err, queueSize: this.outgoingQueue.length },
        'Failed to send Slack message, queued',
      );
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  ownsJid(jid: string): boolean {
    return jid.startsWith('slack:');
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    await this.app.stop();
  }

  // Use a reaction on the user's message as a typing indicator — no extra
  // messages, no thread noise. Add ⏳ when processing starts, remove when done.
  async setTyping(
    jid: string,
    isTyping: boolean,
    messageId?: string,
  ): Promise<void> {
    if (!this.connected || !messageId) return;
    const channelId = jid.replace(/^slack:/, '');

    try {
      if (isTyping) {
        await this.app.client.reactions.add({
          channel: channelId,
          name: 'hourglass_flowing_sand',
          timestamp: messageId,
        });
      } else {
        await this.app.client.reactions.remove({
          channel: channelId,
          name: 'hourglass_flowing_sand',
          timestamp: messageId,
        });
      }
    } catch (err) {
      logger.debug(
        { err, jid, isTyping, messageId },
        'Slack: failed to update typing reaction',
      );
    }
  }

  /**
   * Sync channel metadata from Slack.
   * Fetches channels the bot is a member of and stores their names in the DB.
   */
  async syncChannelMetadata(): Promise<void> {
    try {
      logger.info('Syncing channel metadata from Slack...');
      let cursor: string | undefined;
      let count = 0;

      do {
        const result = await this.app.client.conversations.list({
          types: 'public_channel,private_channel',
          exclude_archived: true,
          limit: 200,
          cursor,
        });

        for (const ch of result.channels || []) {
          if (ch.id && ch.name && ch.is_member) {
            updateChatName(`slack:${ch.id}`, ch.name);
            count++;
          }
        }

        cursor = result.response_metadata?.next_cursor || undefined;
      } while (cursor);

      logger.info({ count }, 'Slack channel metadata synced');
    } catch (err) {
      logger.error({ err }, 'Failed to sync Slack channel metadata');
    }
  }

  /**
   * Auto-register a Slack chat on first interaction.
   * When SLACK_IS_MAIN=true, every Slack chat registers as isMain with no
   * trigger required, giving agents the same full-access mount as the main group.
   */
  private async autoRegister(
    jid: string,
    channelId: string,
    isGroup: boolean,
  ): Promise<void> {
    if (!this.opts.registerGroup) return;

    // Best-effort display name from Slack; fall back to channel id.
    let name = channelId;
    try {
      const info = await this.app.client.conversations.info({
        channel: channelId,
      });
      name =
        info.channel?.name ||
        (info.channel as { user?: string } | undefined)?.user ||
        channelId;
    } catch (err) {
      logger.debug({ err, channelId }, 'conversations.info failed');
    }

    const folder = `slack_${channelId.toLowerCase()}`;
    const trigger = `@${ASSISTANT_NAME}`;
    const isMain = readEnvFile(['SLACK_IS_MAIN']).SLACK_IS_MAIN === 'true';

    logger.info(
      { jid, folder, name, isGroup, isMain },
      'Slack: auto-registering new chat',
    );

    this.opts.registerGroup(jid, {
      name,
      folder,
      trigger,
      added_at: new Date().toISOString(),
      requiresTrigger: isGroup && !isMain,
      isMain,
    });
  }

  /**
   * Promote all already-registered Slack channels to isMain=true when
   * SLACK_IS_MAIN=true. Called on connect so env changes take effect without
   * requiring re-registration.
   */
  private promoteSlackChannels(): void {
    if (!this.opts.registerGroup) return;
    if (readEnvFile(['SLACK_IS_MAIN']).SLACK_IS_MAIN !== 'true') return;

    const groups = this.opts.registeredGroups();
    for (const [jid, existing] of Object.entries(groups)) {
      if (jid.startsWith('slack:') && !existing.isMain) {
        logger.info({ jid }, 'Slack: promoting channel to isMain=true');
        this.opts.registerGroup(jid, {
          ...existing,
          requiresTrigger: false,
          isMain: true,
        });
      }
    }
  }

  private async resolveUserName(userId: string): Promise<string | undefined> {
    if (!userId) return undefined;

    const cached = this.userNameCache.get(userId);
    if (cached) return cached;

    try {
      const result = await this.app.client.users.info({ user: userId });
      const name = result.user?.real_name || result.user?.name;
      if (name) this.userNameCache.set(userId, name);
      return name;
    } catch (err) {
      logger.debug({ userId, err }, 'Failed to resolve Slack user name');
      return undefined;
    }
  }

  private async flushOutgoingQueue(): Promise<void> {
    if (this.flushing || this.outgoingQueue.length === 0) return;
    this.flushing = true;
    try {
      logger.info(
        { count: this.outgoingQueue.length },
        'Flushing Slack outgoing queue',
      );
      while (this.outgoingQueue.length > 0) {
        const item = this.outgoingQueue.shift()!;
        const channelId = item.jid.replace(/^slack:/, '');
        const threadTs = item.replyToMessageId
          ? this.replyThreadTs.get(item.replyToMessageId)
          : undefined;
        await this.app.client.chat.postMessage({
          channel: channelId,
          text: item.text,
          thread_ts: threadTs,
        });
        logger.info(
          { jid: item.jid, length: item.text.length, threadTs },
          'Queued Slack message sent',
        );
      }
    } finally {
      this.flushing = false;
    }
  }
}

registerChannel('slack', (opts: ChannelOpts) => {
  const envVars = readEnvFile(['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']);
  if (!envVars.SLACK_BOT_TOKEN || !envVars.SLACK_APP_TOKEN) {
    logger.warn('Slack: SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set');
    return null;
  }
  return new SlackChannel(opts);
});

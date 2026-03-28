/**
 * RabbitMQ Voice Channel Plugin for OpenClaw
 * 
 * Provides AMQP integration for JavisVoice on Raspberry Pi.
 * Messages flow through RabbitMQ queues instead of HTTP.
 * 
 * Inbound queue (from Pi): javis.voice.in
 * Outbound queue (to Pi): javis.voice.out
 */

import * as amqp from 'amqplib';

const PLUGIN_ID = 'rabbitmq-voice';

interface VoiceMessage {
  sessionId: string;
  text?: string;
  audio?: string;  // base64 encoded audio
  format?: string;
  timestamp: number;
}

interface VoiceResponse {
  sessionId: string;
  response: string;
  timestamp: number;
}

let connection: amqp.Connection | null = null;
let channel: amqp.Channel | null = null;
let isConsuming = false;

function getConfig(api: any): any {
  const cfg = api.config as any;
  return {
    host: cfg?.host ?? 'localhost',
    port: cfg?.port ?? 5672,
    username: cfg?.username ?? 'guest',
    password: cfg?.password ?? 'guest',
    queue: cfg?.queue ?? 'javis.voice.in',
    replyQueue: cfg?.replyQueue ?? 'javis.voice.out',
    vhost: cfg?.vhost ?? '/',
    prefetch: cfg?.prefetch ?? 1,
  };
}

async function connectToRabbitMQ(api: any): Promise<void> {
  const config = getConfig(api);
  const url = `amqp://${config.username}:${config.password}@${config.host}:${config.port}${config.vhost}`;

  api.logger.info(`[${PLUGIN_ID}] Connecting to RabbitMQ at ${config.host}:${config.port}`);

  try {
    connection = await amqp.connect(url);
    channel = await connection.createChannel();

    // Assert both queues exist
    await channel.assertQueue(config.queue, { durable: true });
    await channel.assertQueue(config.replyQueue, { durable: true });
    await channel.prefetch(config.prefetch);

    connection.on('error', (err) => {
      api.logger.error(`[${PLUGIN_ID}] RabbitMQ connection error: ${err.message}`);
    });

    connection.on('close', () => {
      api.logger.warn(`[${PLUGIN_ID}] RabbitMQ connection closed`);
      connection = null;
      channel = null;
      isConsuming = false;
    });

    api.logger.info(`[${PLUGIN_ID}] Connected to RabbitMQ successfully`);
  } catch (err: any) {
    api.logger.error(`[${PLUGIN_ID}] Failed to connect to RabbitMQ: ${err.message}`);
    throw err;
  }
}

async function publishResponse(api: any, sessionId: string, responseText: string): Promise<void> {
  if (!channel) {
    api.logger.warn(`[${PLUGIN_ID}] Cannot publish response - not connected`);
    return;
  }

  const config = getConfig(api);
  const response: VoiceResponse = {
    sessionId,
    response: responseText,
    timestamp: Date.now(),
  };

  channel.sendToQueue(config.replyQueue, Buffer.from(JSON.stringify(response)), {
    persistent: true,
  });

  api.logger.info(`[${PLUGIN_ID}] Published response to ${config.replyQueue}`);
}

async function processVoiceMessage(api: any, msg: VoiceMessage): Promise<void> {
  const { sessionId, text, audio } = msg;

  if (!sessionId) {
    api.logger.warn(`[${PLUGIN_ID}] Message missing sessionId`);
    return;
  }

  if (!text && !audio) {
    api.logger.warn(`[${PLUGIN_ID}] Message missing both text and audio`);
    return;
  }

  api.logger.info(`[${PLUGIN_ID}] Processing message for session: ${sessionId}`);

  // Build a session key for this voice session
  const sessionKey = `rabbitmq:${sessionId}`;

  try {
    // Use the gateway's session.send to process the message
    // This routes it through the normal OpenClaw session flow
    const result = await api.runtime?.rpc?.invoke('session.send', {
      sessionKey,
      channel: 'rabbitmq',
      accountId: 'default',
      message: text || '[Audio Message]',
    });

    if (result?.response) {
      await publishResponse(api, sessionId, result.response);
    } else if (result?.text) {
      await publishResponse(api, sessionId, result.text);
    } else {
      api.logger.warn(`[${PLUGIN_ID}] No response from agent`);
    }
  } catch (err: any) {
    api.logger.error(`[${PLUGIN_ID}] Error processing message: ${err.message}`);
    
    // Send error response back
    await publishResponse(api, sessionId, 'Entschuldigung, es ist ein Fehler aufgetreten.');
  }
}

async function startConsumer(api: any): Promise<void> {
  if (!channel || isConsuming) return;

  const config = getConfig(api);

  await channel.consume(
    config.queue,
    async (msg) => {
      if (!msg) return;

      try {
        const body = JSON.parse(msg.content.toString());
        await processVoiceMessage(api, body);
        channel!.ack(msg);
      } catch (err: any) {
        api.logger.error(`[${PLUGIN_ID}] Failed to process message: ${err.message}`);
        // Negative ack - don't requeue malformed messages
        channel!.nack(msg, false, false);
      }
    },
    { noAck: false }
  );

  isConsuming = true;
  api.logger.info(`[${PLUGIN_ID}] Started consuming from queue: ${config.queue}`);
}

export default function (api: any) {
  // Register the plugin as a service (runs connection + consumer)
  api.registerService({
    id: PLUGIN_ID,
    start: async () => {
      api.logger.info(`[${PLUGIN_ID}] Starting service...`);
      
      try {
        await connectToRabbitMQ(api);
        await startConsumer(api);
        api.logger.info(`[${PLUGIN_ID}] Service started successfully`);
      } catch (err: any) {
        api.logger.error(`[${PLUGIN_ID}] Failed to start: ${err.message}`);
        throw err;
      }
    },
    stop: async () => {
      api.logger.info(`[${PLUGIN_ID}] Stopping service...`);
      isConsuming = false;

      if (channel) {
        try {
          await channel.close();
        } catch (e) {
          // ignore close errors
        }
        channel = null;
      }

      if (connection) {
        try {
          await connection.close();
        } catch (e) {
          // ignore close errors
        }
        connection = null;
      }

      api.logger.info(`[${PLUGIN_ID}] Service stopped`);
    },
  });

  // Gateway RPC methods for external access
  api.registerGatewayMethod(`${PLUGIN_ID}.status`, ({ respond }: any) => {
    respond(true, {
      plugin: PLUGIN_ID,
      connected: connection !== null && channel !== null,
      consuming: isConsuming,
      config: {
        queue: getConfig(api).queue,
        replyQueue: getConfig(api).replyQueue,
      },
    });
  });

  // Method to manually publish a message (for testing or other plugins)
  api.registerGatewayMethod(`${PLUGIN_ID}.publish`, ({ respond, body }: any) => {
    if (!channel) {
      respond(false, { error: 'Not connected to RabbitMQ' });
      return;
    }

    const config = getConfig(api);
    const { sessionId, text } = body || {};

    if (!sessionId || !text) {
      respond(false, { error: 'Missing sessionId or text' });
      return;
    }

    const message: VoiceMessage = {
      sessionId,
      text,
      timestamp: Date.now(),
    };

    channel.sendToQueue(config.queue, Buffer.from(JSON.stringify(message)), {
      persistent: true,
    });

    respond(true, { queued: true, queue: config.queue });
  });
}

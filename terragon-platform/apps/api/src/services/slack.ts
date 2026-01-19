import { prisma } from '@terragon/database';
import { logger } from '@terragon/shared';

const log = logger.child('slack');

export interface SlackMessage {
  text?: string;
  blocks?: SlackBlock[];
  attachments?: SlackAttachment[];
}

export interface SlackBlock {
  type: string;
  text?: {
    type: string;
    text: string;
    emoji?: boolean;
  };
  elements?: Array<{
    type: string;
    text?: { type: string; text: string; emoji?: boolean };
    url?: string;
    action_id?: string;
  }>;
  accessory?: {
    type: string;
    text?: { type: string; text: string; emoji?: boolean };
    url?: string;
    action_id?: string;
  };
}

export interface SlackAttachment {
  color?: string;
  title?: string;
  title_link?: string;
  text?: string;
  fields?: Array<{ title: string; value: string; short?: boolean }>;
  footer?: string;
  ts?: number;
}

export interface TaskNotificationData {
  taskId: string;
  taskTitle: string;
  repository: string;
  status: 'started' | 'completed' | 'failed';
  agent: string;
  pullRequestUrl?: string | null;
  errorMessage?: string | null;
  executionTime?: number | null;
  creditsUsed?: number;
}

class SlackNotificationService {
  /**
   * Send a notification to Slack for a user
   */
  async sendNotification(userId: string, message: SlackMessage): Promise<boolean> {
    try {
      const integration = await prisma.integration.findFirst({
        where: {
          userId,
          type: 'SLACK',
          isActive: true,
        },
      });

      if (!integration || !integration.accessToken) {
        log.debug('No active Slack integration for user', { userId });
        return false;
      }

      const response = await fetch(integration.accessToken, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(message),
      });

      if (!response.ok) {
        log.error('Failed to send Slack notification', {
          userId,
          status: response.status,
        });
        return false;
      }

      log.info('Slack notification sent', { userId });
      return true;
    } catch (error) {
      log.error('Error sending Slack notification', { userId, error });
      return false;
    }
  }

  /**
   * Send a task started notification
   */
  async notifyTaskStarted(userId: string, data: TaskNotificationData): Promise<boolean> {
    const message: SlackMessage = {
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: 'Task Started',
            emoji: true,
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*${data.taskTitle}*\n${data.repository}`,
          },
          accessory: {
            type: 'button',
            text: {
              type: 'plain_text',
              text: 'View Task',
              emoji: true,
            },
            url: `${process.env.FRONTEND_URL}/dashboard/tasks/${data.taskId}`,
          },
        },
        {
          type: 'context',
          elements: [
            {
              type: 'mrkdwn',
              text: `Agent: *${data.agent}*`,
            },
          ],
        },
      ],
    };

    return this.sendNotification(userId, message);
  }

  /**
   * Send a task completed notification
   */
  async notifyTaskCompleted(userId: string, data: TaskNotificationData): Promise<boolean> {
    const fields: Array<{ title: string; value: string; short?: boolean }> = [];

    if (data.executionTime) {
      fields.push({
        title: 'Execution Time',
        value: `${Math.round(data.executionTime / 60)} min`,
        short: true,
      });
    }

    if (data.creditsUsed !== undefined) {
      fields.push({
        title: 'Credits Used',
        value: String(data.creditsUsed),
        short: true,
      });
    }

    const blocks: SlackBlock[] = [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: 'Task Completed',
          emoji: true,
        },
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*${data.taskTitle}*\n${data.repository}`,
        },
      },
    ];

    if (data.pullRequestUrl) {
      blocks.push({
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `Pull request created and ready for review.`,
        },
        accessory: {
          type: 'button',
          text: {
            type: 'plain_text',
            text: 'View PR',
            emoji: true,
          },
          url: data.pullRequestUrl,
        },
      });
    }

    blocks.push({
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `Agent: *${data.agent}* | ${fields.map((f) => `${f.title}: ${f.value}`).join(' | ')}`,
        },
      ],
    });

    const message: SlackMessage = {
      blocks,
      attachments: [
        {
          color: '#36a64f', // Green
          footer: 'Terragon',
          ts: Math.floor(Date.now() / 1000),
        },
      ],
    };

    return this.sendNotification(userId, message);
  }

  /**
   * Send a task failed notification
   */
  async notifyTaskFailed(userId: string, data: TaskNotificationData): Promise<boolean> {
    const message: SlackMessage = {
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: 'Task Failed',
            emoji: true,
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*${data.taskTitle}*\n${data.repository}`,
          },
          accessory: {
            type: 'button',
            text: {
              type: 'plain_text',
              text: 'View Task',
              emoji: true,
            },
            url: `${process.env.FRONTEND_URL}/dashboard/tasks/${data.taskId}`,
          },
        },
      ],
      attachments: [
        {
          color: '#dc3545', // Red
          title: 'Error',
          text: data.errorMessage || 'An unknown error occurred',
          footer: 'Terragon',
          ts: Math.floor(Date.now() / 1000),
        },
      ],
    };

    return this.sendNotification(userId, message);
  }

  /**
   * Send a custom notification
   */
  async sendCustomNotification(
    userId: string,
    title: string,
    message: string,
    color?: string,
    actionUrl?: string,
    actionText?: string
  ): Promise<boolean> {
    const blocks: SlackBlock[] = [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: title,
          emoji: true,
        },
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: message,
        },
      },
    ];

    if (actionUrl && actionText) {
      blocks.push({
        type: 'actions',
        elements: [
          {
            type: 'button',
            text: {
              type: 'plain_text',
              text: actionText,
              emoji: true,
            },
            url: actionUrl,
          },
        ],
      });
    }

    const slackMessage: SlackMessage = {
      blocks,
      attachments: color
        ? [
            {
              color,
              footer: 'Terragon',
              ts: Math.floor(Date.now() / 1000),
            },
          ]
        : undefined,
    };

    return this.sendNotification(userId, slackMessage);
  }

  /**
   * Send automation triggered notification
   */
  async notifyAutomationTriggered(
    userId: string,
    automationName: string,
    taskId: string,
    triggerSource: string
  ): Promise<boolean> {
    const message: SlackMessage = {
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: 'Automation Triggered',
            emoji: true,
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*${automationName}*\nTriggered by: ${triggerSource}`,
          },
          accessory: {
            type: 'button',
            text: {
              type: 'plain_text',
              text: 'View Task',
              emoji: true,
            },
            url: `${process.env.FRONTEND_URL}/dashboard/tasks/${taskId}`,
          },
        },
      ],
      attachments: [
        {
          color: '#007bff', // Blue
          footer: 'Terragon Automations',
          ts: Math.floor(Date.now() / 1000),
        },
      ],
    };

    return this.sendNotification(userId, message);
  }

  /**
   * Send credits low warning
   */
  async notifyCreditsLow(userId: string, currentCredits: number, threshold: number): Promise<boolean> {
    const message: SlackMessage = {
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: 'Credits Running Low',
            emoji: true,
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `You have *${currentCredits}* credits remaining (below ${threshold} threshold).\n\nConsider upgrading your plan or purchasing additional credits to avoid task interruptions.`,
          },
          accessory: {
            type: 'button',
            text: {
              type: 'plain_text',
              text: 'Manage Billing',
              emoji: true,
            },
            url: `${process.env.FRONTEND_URL}/dashboard/billing`,
          },
        },
      ],
      attachments: [
        {
          color: '#ffc107', // Yellow/Warning
          footer: 'Terragon',
          ts: Math.floor(Date.now() / 1000),
        },
      ],
    };

    return this.sendNotification(userId, message);
  }
}

export const slackService = new SlackNotificationService();

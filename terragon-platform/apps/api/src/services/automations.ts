import cron from 'node-cron';
import { v4 as uuidv4 } from 'uuid';

export type AutomationTriggerType = 'schedule' | 'github' | 'slack' | 'webhook';

export interface ScheduleTrigger {
  type: 'schedule';
  cron: string; // Cron expression (e.g., "0 9 * * *" for daily at 9am)
  timezone?: string;
}

export interface GitHubTrigger {
  type: 'github';
  events: Array<'push' | 'pull_request' | 'issue' | 'release' | 'issue_comment'>;
  branches?: string[];
  paths?: string[];
}

export interface SlackTrigger {
  type: 'slack';
  channel?: string;
  keywords?: string[];
  mentionOnly?: boolean;
}

export interface WebhookTrigger {
  type: 'webhook';
  secret?: string;
}

export type AutomationTrigger =
  | ScheduleTrigger
  | GitHubTrigger
  | SlackTrigger
  | WebhookTrigger;

export interface Automation {
  id: string;
  userId: string;
  name: string;
  description?: string;
  enabled: boolean;
  trigger: AutomationTrigger;
  task: {
    repository: string;
    prompt: string;
    agent: string;
    branch?: string;
  };
  createdAt: Date;
  updatedAt: Date;
  lastRunAt?: Date;
  nextRunAt?: Date;
  runCount: number;
}

export interface AutomationRun {
  id: string;
  automationId: string;
  taskId?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  triggeredBy: string;
  startedAt: Date;
  completedAt?: Date;
  error?: string;
}

/**
 * Automations Service
 *
 * Manages scheduled and event-triggered task automations
 */
class AutomationsService {
  private automations: Map<string, Automation> = new Map();
  private scheduledJobs: Map<string, cron.ScheduledTask> = new Map();
  private runs: Map<string, AutomationRun> = new Map();
  private onTaskCreate?: (automation: Automation, triggeredBy: string) => Promise<string>;

  setTaskCreateHandler(handler: (automation: Automation, triggeredBy: string) => Promise<string>) {
    this.onTaskCreate = handler;
  }

  async create(
    userId: string,
    config: Omit<Automation, 'id' | 'createdAt' | 'updatedAt' | 'runCount'>
  ): Promise<Automation> {
    const id = `auto_${uuidv4().replace(/-/g, '').slice(0, 12)}`;

    const automation: Automation = {
      ...config,
      id,
      userId,
      createdAt: new Date(),
      updatedAt: new Date(),
      runCount: 0,
    };

    this.automations.set(id, automation);

    // Schedule if it's a cron trigger
    if (automation.enabled && automation.trigger.type === 'schedule') {
      this.scheduleAutomation(automation);
    }

    console.log(`[Automations] Created automation: ${automation.name} (${id})`);
    return automation;
  }

  async update(
    id: string,
    updates: Partial<Omit<Automation, 'id' | 'userId' | 'createdAt'>>
  ): Promise<Automation | null> {
    const automation = this.automations.get(id);
    if (!automation) return null;

    // Stop existing schedule if any
    this.unscheduleAutomation(id);

    Object.assign(automation, updates, { updatedAt: new Date() });
    this.automations.set(id, automation);

    // Reschedule if enabled and is a schedule trigger
    if (automation.enabled && automation.trigger.type === 'schedule') {
      this.scheduleAutomation(automation);
    }

    return automation;
  }

  async delete(id: string): Promise<boolean> {
    this.unscheduleAutomation(id);
    return this.automations.delete(id);
  }

  async get(id: string): Promise<Automation | null> {
    return this.automations.get(id) || null;
  }

  async list(userId: string): Promise<Automation[]> {
    return Array.from(this.automations.values())
      .filter((a) => a.userId === userId);
  }

  async enable(id: string): Promise<boolean> {
    const automation = this.automations.get(id);
    if (!automation) return false;

    automation.enabled = true;
    automation.updatedAt = new Date();

    if (automation.trigger.type === 'schedule') {
      this.scheduleAutomation(automation);
    }

    return true;
  }

  async disable(id: string): Promise<boolean> {
    const automation = this.automations.get(id);
    if (!automation) return false;

    automation.enabled = false;
    automation.updatedAt = new Date();
    this.unscheduleAutomation(id);

    return true;
  }

  private scheduleAutomation(automation: Automation) {
    if (automation.trigger.type !== 'schedule') return;

    const { cron: cronExpr, timezone } = automation.trigger;

    try {
      const job = cron.schedule(
        cronExpr,
        async () => {
          console.log(`[Automations] Running scheduled automation: ${automation.name}`);
          await this.triggerAutomation(automation.id, 'schedule');
        },
        {
          timezone: timezone || 'UTC',
          scheduled: true,
        }
      );

      this.scheduledJobs.set(automation.id, job);

      // Calculate next run time
      const parser = require('cron-parser');
      const interval = parser.parseExpression(cronExpr, { tz: timezone || 'UTC' });
      automation.nextRunAt = interval.next().toDate();

      console.log(
        `[Automations] Scheduled ${automation.name} - next run: ${automation.nextRunAt}`
      );
    } catch (error) {
      console.error(`[Automations] Failed to schedule ${automation.name}:`, error);
    }
  }

  private unscheduleAutomation(id: string) {
    const job = this.scheduledJobs.get(id);
    if (job) {
      job.stop();
      this.scheduledJobs.delete(id);
    }
  }

  async triggerAutomation(id: string, triggeredBy: string): Promise<AutomationRun | null> {
    const automation = this.automations.get(id);
    if (!automation || !automation.enabled) return null;

    const runId = `run_${uuidv4().replace(/-/g, '').slice(0, 12)}`;
    const run: AutomationRun = {
      id: runId,
      automationId: id,
      status: 'pending',
      triggeredBy,
      startedAt: new Date(),
    };

    this.runs.set(runId, run);

    try {
      run.status = 'running';

      if (this.onTaskCreate) {
        run.taskId = await this.onTaskCreate(automation, triggeredBy);
      }

      run.status = 'completed';
      run.completedAt = new Date();

      automation.lastRunAt = new Date();
      automation.runCount++;

      // Update next run time for schedule triggers
      if (automation.trigger.type === 'schedule') {
        const parser = require('cron-parser');
        const interval = parser.parseExpression(automation.trigger.cron, {
          tz: automation.trigger.timezone || 'UTC',
        });
        automation.nextRunAt = interval.next().toDate();
      }

      console.log(`[Automations] Run completed: ${runId} -> Task ${run.taskId}`);
    } catch (error) {
      run.status = 'failed';
      run.completedAt = new Date();
      run.error = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[Automations] Run failed: ${runId}`, error);
    }

    return run;
  }

  // Handle GitHub webhook events
  async handleGitHubEvent(
    event: string,
    payload: {
      repository: { full_name: string };
      ref?: string;
      action?: string;
    }
  ): Promise<AutomationRun[]> {
    const runs: AutomationRun[] = [];
    const repoName = payload.repository.full_name;
    const branch = payload.ref?.replace('refs/heads/', '');

    for (const automation of this.automations.values()) {
      if (!automation.enabled) continue;
      if (automation.trigger.type !== 'github') continue;
      if (automation.task.repository !== repoName) continue;

      const trigger = automation.trigger;

      // Check if event matches
      const eventMatches = trigger.events.some((e) => {
        if (e === 'push' && event === 'push') return true;
        if (e === 'pull_request' && event === 'pull_request') return true;
        if (e === 'issue' && event === 'issues') return true;
        if (e === 'release' && event === 'release') return true;
        if (e === 'issue_comment' && event === 'issue_comment') return true;
        return false;
      });

      if (!eventMatches) continue;

      // Check branch filter
      if (trigger.branches && branch && !trigger.branches.includes(branch)) {
        continue;
      }

      const run = await this.triggerAutomation(
        automation.id,
        `github:${event}`
      );
      if (run) runs.push(run);
    }

    return runs;
  }

  // Handle Slack message events
  async handleSlackMessage(
    channelId: string,
    message: string,
    isMention: boolean
  ): Promise<AutomationRun[]> {
    const runs: AutomationRun[] = [];

    for (const automation of this.automations.values()) {
      if (!automation.enabled) continue;
      if (automation.trigger.type !== 'slack') continue;

      const trigger = automation.trigger;

      // Check channel filter
      if (trigger.channel && trigger.channel !== channelId) continue;

      // Check mention filter
      if (trigger.mentionOnly && !isMention) continue;

      // Check keyword filter
      if (trigger.keywords?.length) {
        const hasKeyword = trigger.keywords.some((k) =>
          message.toLowerCase().includes(k.toLowerCase())
        );
        if (!hasKeyword) continue;
      }

      const run = await this.triggerAutomation(automation.id, 'slack:message');
      if (run) runs.push(run);
    }

    return runs;
  }

  // Handle webhook triggers
  async handleWebhook(
    automationId: string,
    payload: unknown
  ): Promise<AutomationRun | null> {
    const automation = this.automations.get(automationId);
    if (!automation || !automation.enabled) return null;
    if (automation.trigger.type !== 'webhook') return null;

    return this.triggerAutomation(automationId, `webhook:${JSON.stringify(payload).slice(0, 50)}`);
  }

  async getRuns(automationId: string, limit: number = 10): Promise<AutomationRun[]> {
    return Array.from(this.runs.values())
      .filter((r) => r.automationId === automationId)
      .sort((a, b) => b.startedAt.getTime() - a.startedAt.getTime())
      .slice(0, limit);
  }
}

export const automationsService = new AutomationsService();

/**
 * CollaborationManager - DEPRECATED
 *
 * Multi-agent collaboration has been disabled.
 * Single-agent direct execution mode is now used.
 *
 * Architecture change:
 * - OLD: CollaborationManager with pipeline/parallel/discussion modes
 * - NEW: MainAgent.think() → LLM Loop → Tools → Direct Response
 *
 * @deprecated Use single-agent direct execution instead
 */
export type CollaborationMode = 'pipeline' | 'parallel' | 'discussion';

interface CollaborationTask {
  id: string;
  mode: CollaborationMode;
  participants: string[];
  status: 'pending' | 'in_progress' | 'completed';
  results: Map<string, unknown>;
}

export class CollaborationManager {
  private activeTasks: Map<string, CollaborationTask> = new Map();

  createCollaboration(
    taskId: string,
    mode: CollaborationMode,
    participants: string[]
  ): CollaborationTask {
    throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
  }

  getCollaboration(taskId: string): CollaborationTask | undefined {
    return undefined;
  }

  async executePipeline(taskId: string, executeFn: (role: string) => Promise<unknown>): Promise<unknown[]> {
    throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
  }

  async executeParallel(taskId: string, executeFn: (role: string) => Promise<unknown>): Promise<Map<string, unknown>> {
    throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
  }

  async executeDiscussion(
    taskId: string,
    executeFn: (role: string) => Promise<unknown>,
    consensusFn: (results: unknown[]) => unknown
  ): Promise<unknown> {
    throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
  }

  completeCollaboration(taskId: string): void {
    // No-op
  }
}

export const collaborationManager = new CollaborationManager();
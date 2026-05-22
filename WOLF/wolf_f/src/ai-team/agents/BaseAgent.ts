/**
 * BaseAgent - DEPRECATED
 *
 * Multi-agent collaboration has been disabled.
 * Single-agent direct execution mode is now used.
 *
 * @deprecated Use MainAgent with single-agent direct execution instead
 */
export abstract class BaseAgent {
  constructor(
    id: string,
    role: string,
    name: string,
    systemPrompt: string
  ) {
    throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
  }

  abstract execute(task: unknown): Promise<string>;

  async receive(message: unknown): Promise<void> {
    throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
  }
}
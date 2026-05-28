/**
 * AgentWorkflow - DEPRECATED component
 *
 * Multi-agent collaboration has been disabled.
 * This stub exists to prevent import errors during migration.
 *
 * Architecture change:
 * - OLD: MainAgent → SharedWorkspace → MultiAgents → Collaboration
 * - NEW: MainAgent.think() → LLM Loop → Tools → Direct Response
 *
 * @deprecated Use MainAgent with single-agent direct execution mode instead
 */
import React from 'react';

interface AgentWorkflowProps {
  role: string | null;
}

export function AgentWorkflow({ role }: AgentWorkflowProps) {
  return (
    <div className="flex-1 flex items-center justify-center bg-vscode-bg">
      <div className="text-center text-vscode-text-dim">
        <p className="text-lg mb-2">Multi-agent collaboration disabled</p>
        <p className="text-sm">
          Using single-agent direct execution mode.
        </p>
        {role && (
          <p className="text-xs mt-2 text-vscode-accent">
            (Agent: {role})
          </p>
        )}
      </div>
    </div>
  );
}

export default AgentWorkflow;

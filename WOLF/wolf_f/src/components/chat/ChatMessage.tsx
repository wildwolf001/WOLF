import React from 'react';
import type { ChatMessage as ChatMessageType } from '@/types';
import clsx from 'clsx';

interface ChatMessageProps {
  message: ChatMessageType;
}

const roleLabels: Record<string, string> = {
  pm: 'PM',
  research: 'Researcher',
  ml: 'ML Engineer',
  developer: 'Developer',
  writer: 'Writer',
  data: 'Data Engineer',
  review: 'Reviewer',
  devops: 'DevOps',
  user: 'You',
};

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.isUser;

  return (
    <div className={clsx('flex gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={clsx(
          'w-8 h-8 rounded-sm flex items-center justify-center text-xs font-medium flex-shrink-0',
          isUser ? 'bg-vscode-accent text-white' : 'bg-vscode-bg-hover text-vscode-text'
        )}
      >
        {isUser ? 'U' : roleLabels[message.agentRole]?.[0] || 'A'}
      </div>

      <div
        className={clsx(
          'max-w-[70%] rounded-sm p-3',
          isUser ? 'bg-vscode-accent text-white' : 'bg-vscode-bg-light border border-vscode-border'
        )}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className={clsx('text-xs font-medium', isUser ? 'text-white/80' : 'text-vscode-text-dim')}>
            {isUser ? 'You' : roleLabels[message.agentRole] || message.agentRole}
          </span>
          <span className={clsx('text-xs', isUser ? 'text-white/60' : 'text-vscode-text-dim')}>
            {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ''}
          </span>
        </div>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
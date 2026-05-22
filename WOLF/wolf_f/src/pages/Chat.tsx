import React from 'react';
import { ChatWindow } from '@/components/chat/ChatWindow';

export function Chat() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ChatWindow />
    </div>
  );
}
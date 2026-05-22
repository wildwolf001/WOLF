import React from 'react';
import { KnowledgeSearch } from '@/components/knowledge';

export function Knowledge() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium mb-2">Knowledge Base</h2>
        <p className="text-sm text-gray-400">
          Search through papers, documents, and research materials
        </p>
      </div>
      <KnowledgeSearch />
    </div>
  );
}

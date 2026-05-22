export interface KnowledgeEntry {
  id: string;
  content: string;
  source: string;
  sourceType: 'paper' | 'document' | 'web' | 'conversation';
  embedding?: number[];
  metadata: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
}

export class KnowledgeBase {
  private entries: Map<string, KnowledgeEntry> = new Map();

  async addEntry(entry: Omit<KnowledgeEntry, 'id' | 'createdAt' | 'updatedAt'>): Promise<KnowledgeEntry> {
    const newEntry: KnowledgeEntry = {
      ...entry,
      id: `kb-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    this.entries.set(newEntry.id, newEntry);
    return newEntry;
  }

  getEntry(id: string): KnowledgeEntry | undefined {
    return this.entries.get(id);
  }

  getAllEntries(): KnowledgeEntry[] {
    return Array.from(this.entries.values());
  }

  search(query: string, limit: number = 10): KnowledgeEntry[] {
    // Simple text search - in real implementation, this would use vector similarity
    const queryLower = query.toLowerCase();
    return this.getAllEntries()
      .filter((entry) =>
        entry.content.toLowerCase().includes(queryLower) ||
        entry.source.toLowerCase().includes(queryLower)
      )
      .slice(0, limit);
  }

  async semanticSearch(embedding: number[], limit: number = 10): Promise<KnowledgeEntry[]> {
    // In real implementation, this would compute cosine similarity
    // For now, return entries with similar content
    return this.getAllEntries().slice(0, limit);
  }

  deleteEntry(id: string): boolean {
    return this.entries.delete(id);
  }

  updateEntry(id: string, updates: Partial<KnowledgeEntry>): KnowledgeEntry | undefined {
    const entry = this.entries.get(id);
    if (!entry) return undefined;

    const updated = { ...entry, ...updates, updatedAt: Date.now() };
    this.entries.set(id, updated);
    return updated;
  }

  getStats(): { total: number; byType: Record<string, number> } {
    const entries = this.getAllEntries();
    const byType: Record<string, number> = {};

    entries.forEach((entry) => {
      byType[entry.sourceType] = (byType[entry.sourceType] || 0) + 1;
    });

    return { total: entries.length, byType };
  }
}

export const knowledgeBase = new KnowledgeBase();

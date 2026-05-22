import React, { useState } from 'react';
import { knowledgeApi } from '@/services/api';

export function KnowledgeSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<unknown[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    try {
      const response = await knowledgeApi.search(query);
      const data = response as any;
      if (data.success && data.data) {
        setResults(data.data as unknown[] || []);
      } else {
        setResults([]);
      }
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    }
    setIsSearching(false);
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search knowledge base..."
          className="flex-1 px-4 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:border-primary-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={isSearching}
          className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 rounded-lg font-medium transition-colors"
        >
          {isSearching ? 'Searching...' : 'Search'}
        </button>
      </form>

      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((result: any) => (
            <div
              key={result.id}
              className="p-4 bg-gray-800 rounded-lg border border-gray-700"
            >
              <h3 className="font-medium">{result.full_content || result.content || result.title}</h3>
              {result.metadata?.source && (
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded">
                    {result.metadata.source}
                  </span>
                </div>
              )}
              <p className="text-xs text-gray-400 mt-2 line-clamp-2">
                Score: {(result.score || 0).toFixed(2)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

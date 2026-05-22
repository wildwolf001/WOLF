import { create } from 'zustand';

interface Document {
  id: string;
  title: string;
  content: string;
  type: 'paper' | 'plan' | 'doc';
  version: number;
  taskId?: string;
  createdAt: number;
  updatedAt: number;
}

interface DocumentStore {
  documents: Document[];
  selectedDocument: Document | null;
  addDocument: (doc: Omit<Document, 'id' | 'version' | 'createdAt' | 'updatedAt'>) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
  deleteDocument: (id: string) => void;
  setSelectedDocument: (doc: Document | null) => void;
}

export const useDocumentStore = create<DocumentStore>((set) => ({
  documents: [],
  selectedDocument: null,

  addDocument: (doc) =>
    set((state) => ({
      documents: [
        ...state.documents,
        {
          ...doc,
          id: `doc-${Date.now()}`,
          version: 1,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      ],
    })),

  updateDocument: (id, updates) =>
    set((state) => ({
      documents: state.documents.map((d) =>
        d.id === id ? { ...d, ...updates, updatedAt: Date.now() } : d
      ),
    })),

  deleteDocument: (id) =>
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== id),
      selectedDocument: state.selectedDocument?.id === id ? null : state.selectedDocument,
    })),

  setSelectedDocument: (doc) => set({ selectedDocument: doc }),
}));

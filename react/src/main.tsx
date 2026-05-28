import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Expose stores for Settings page memory management
import { useSessionStore } from './store/sessionStore';
(window as any).__WOLF_STORES__ = {
  sessionStore: { getState: useSessionStore.getState }
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

# WOLF - AI Research Team Platform

A multi-agent AI research team collaboration platform that simulates a real research team workflow.

## Project Structure

```
WOLF/
├── wolf_f/          # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── store/         # Zustand state management
│   │   ├── services/      # API and WebSocket services
│   │   ├── pages/         # Page components
│   │   ├── types/         # TypeScript types
│   │   └── ai-team/       # AI team core modules
│   └── package.json
│
└── wolf_b/          # Backend (Python FastAPI)
    ├── app/
    │   ├── agents/         # Agent implementations
    │   ├── api/           # REST API routes
    │   ├── db/            # Database models and schemas
    │   ├── ws/            # WebSocket handlers
    │   └── core/          # Configuration
    └── requirements.txt
```

## Features

### AI Agents (8 Roles)
- **PM Agent**: Project manager - coordinates tasks and team
- **Research Agent**: Literature review and information gathering
- **ML Engineer Agent**: Model development, training, optimization
- **Developer Agent**: Full-stack development
- **Writer Agent**: Technical writing and documentation
- **Data Agent**: Data collection, cleaning, annotation
- **Review Agent**: Paper quality control and review
- **DevOps Agent**: Deployment and infrastructure

### Core Capabilities
- Multi-agent collaboration (Pipeline, Parallel, Discussion modes)
- Task management with automatic assignment
- Real-time chat with agents
- Document management
- Knowledge base with RAG
- WebSocket real-time updates

## Setup

### Frontend
```bash
cd wolf_f
npm install
npm run dev
```

### Backend
```bash
cd wolf_b
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tech Stack

**Frontend**: React 18, TypeScript, TailwindCSS, Zustand, Socket.io
**Backend**: FastAPI, SQLAlchemy, WebSocket, Pydantic

## License

MIT

import { create } from 'zustand';
import type { AgentConfig, AgentRole, AgentStatus } from '@/types';

interface AgentStore {
  agents: AgentConfig[];
  activeAgent: string | null;
  setAgents: (agents: AgentConfig[]) => void;
  setActiveAgent: (id: string | null) => void;
  updateAgentStatus: (id: string, status: AgentStatus) => void;
  getAgentByRole: (role: AgentRole) => AgentConfig | undefined;
}

// Default agent configurations
const defaultAgents: AgentConfig[] = [
  {
    id: 'main-001',
    role: 'main',
    name: 'Main Agent',
    description: 'Main Agent (Claude Code style) - Single agent that handles all tasks using tools',
    systemPrompt: `You are the WOLF Main Agent, inspired by Claude Code's single-agent architecture.

You handle all user requests directly using tools:
- list_directory, read, grep, glob, bash, write, edit

Your approach:
1. First explore to understand the task
2. Decide which tools to use
3. Execute and return results
4. No task decomposition - you handle it directly`,
    status: 'idle',
    capabilities: ['coordination', 'execution', 'analysis', 'exploration'],
  },
  {
    id: 'pm-001',
    role: 'pm',
    name: 'PM Agent',
    description: 'Project Manager - Coordinates tasks (legacy)',
    systemPrompt: `You are an experienced research project manager (PM).
Your responsibilities:
1. Receive user research/development requirements
2. Break complex tasks into subtasks
3. Assign tasks to appropriate agents based on expertise
4. Track progress and coordinate resources
5. Report when tasks are completed or issues arise

Communication style: Professional, concise, organized.`,
    status: 'idle',
    capabilities: ['task-management', 'coordination', 'planning'],
  },
  {
    id: 'research-001',
    role: 'research',
    name: 'Research Agent',
    description: 'Research Agent - Literature review and information gathering',
    systemPrompt: `You are a professional AI researcher specializing in literature review.
Your expertise: LLM, CV, Agent, Deep Learning.

You can:
1. Understand user research directions and needs
2. Search related papers (via API or database)
3. Deep read and extract key info: methods, contributions, limitations
4. Organize into structured literature reports
5. Answer "What are the mainstream methods in this direction?"

Output format: Structured Markdown with paper title, authors, core methods, key conclusions.`,
    status: 'idle',
    capabilities: ['web-search', 'paper-analysis', 'knowledge-synthesis'],
  },
  {
    id: 'ml-001',
    role: 'ml',
    name: 'ML Engineer Agent',
    description: 'ML Engineer - Model development, training, optimization',
    systemPrompt: `You are a senior ML engineer specializing in deep learning.

You are responsible for:
1. Design appropriate model architectures based on requirements
2. Write high-quality training code
3. Implement training strategies (data augmentation, LR scheduling, etc.)
4. Analyze experimental results and propose improvements
5. Optimize model performance (inference speed, memory usage)

Tech stack: PyTorch, TensorFlow, JAX, DeepSpeed, vLLM
Code style: Modular, reproducible, with comments.`,
    status: 'idle',
    capabilities: ['model-design', 'training', 'optimization', 'distributed-training'],
  },
  {
    id: 'developer-001',
    role: 'developer',
    name: 'Developer Agent',
    description: 'Full-Stack Developer - System platform development',
    systemPrompt: `You are a full-stack software engineer responsible for project development.

You can:
1. Understand product requirements and convert to technical solutions
2. Write frontend pages and interaction logic
3. Develop backend services and APIs
4. Design database schemas
5. Write test cases
6. Review and optimize code

Tech stack: React, TypeScript, Node.js, Python, PostgreSQL, Docker
Code standards: Clean Code, Type Safety, with tests.`,
    status: 'idle',
    capabilities: ['frontend', 'backend', 'database', 'devops'],
  },
  {
    id: 'writer-001',
    role: 'writer',
    name: 'Writer Agent',
    description: 'Technical Writer - Paper and document writing',
    systemPrompt: `You are a professional academic writer specializing in research papers and technical documents.

You are responsible for:
1. Paper writing: Abstract, Introduction, Related Work, Method, Experiment, Conclusion
2. Project proposals: Background, objectives, technical roadmap, expected outcomes, budget
3. Technical documents: API docs, design docs, user manuals
4. Polishing and rewriting: Improve language quality

Writing standards: IEEE/ACM format, LaTeX friendly.`,
    status: 'idle',
    capabilities: ['paper-writing', 'documentation', 'translation', 'polishing'],
  },
  {
    id: 'data-001',
    role: 'data',
    name: 'Data Agent',
    description: 'Data Engineer - Data collection, cleaning, annotation',
    systemPrompt: `You are a professional data engineer.

You are responsible for:
1. Understand data requirements
2. Design data collection plans (crawler scripts / API calls)
3. Data cleaning: deduplication, missing value handling, format unification
4. Data annotation:制定标注规范，管理标注质量
5. Dataset version management
6. Build RAG knowledge base

Tools: Python, Pandas, Scrapy, Label Studio, DVC.`,
    status: 'idle',
    capabilities: ['data-collection', 'data-cleaning', 'annotation', 'version-control'],
  },
  {
    id: 'review-001',
    role: 'review',
    name: 'Review Agent',
    description: 'Review Agent - Paper quality control and revision suggestions',
    systemPrompt: `You are a senior research review expert, have served as conference reviewer.

You are responsible for:
1. Paper overall structure review: is logic clear?
2. Methodology evaluation: Is innovation clear? Are experiments sufficient?
3. Writing quality: Is expression accurate? Is terminology professional?
4. Completeness check: Are important citations missing? Related work?
5. Specific improvement suggestions: What needs to be added? How to strengthen?

Review dimensions: Innovation, Completeness, Correctness, Reproducibility, Writing Quality.`,
    status: 'idle',
    capabilities: ['paper-review', 'quality-control', 'feedback'],
  },
  {
    id: 'devops-001',
    role: 'devops',
    name: 'DevOps Agent',
    description: 'DevOps Agent - Environment configuration and deployment',
    systemPrompt: `You are a senior DevOps engineer specializing in cloud-native and MLOps.

You are responsible for:
1. Environment configuration: Dockerfile, docker-compose
2. Deployment solutions: K8s / Serverless / VM
3. CI/CD: GitHub Actions / GitLab CI
4. Monitoring alerts: Prometheus, Grafana
5. Performance optimization: GPU utilization, load balancing
6. Troubleshooting: Log analysis, problem location

Tools: Docker, K8s, Terraform, Ansible, Prometheus, Grafana.`,
    status: 'idle',
    capabilities: ['containerization', 'ci-cd', 'monitoring', 'infrastructure'],
  },
];

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: defaultAgents,
  activeAgent: null,
  setAgents: (agents) => set({ agents }),
  setActiveAgent: (id) => set({ activeAgent: id }),
  updateAgentStatus: (id, status) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, status } : a)),
    })),
  getAgentByRole: (role) => get().agents.find((a) => a.role === role),
}));

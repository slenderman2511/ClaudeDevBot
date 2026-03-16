# ClaudeDevBot Embedded Library - Design Specification

**Date:** 2026-03-16
**Topic:** Embedded Library - Multi-Channel AI Development Assistant
**Status:** Pending Review

---

## 1. Executive Summary

Thiết kế hệ thống ClaudeDevBot như một embedded library/API service cho phép teams sử dụng AI-driven development workflows qua nhiều channels (Web, Telegram, REST API). Hệ thống hỗ trợ đa ngôn ngữ (Python, JavaScript/TypeScript) và deploy linh hoạt (self-hosted, cloud, local).

---

## 2. Goals & Non-Goals

### Goals
- Cung cấp AI development assistant qua Web UI, Telegram, và REST API
- Hỗ trợ đầy đủ workflows: Spec Generation, Code Generation, Testing, Debugging
- Multi-channel sync: Task được start ở channel này có thể xem progress ở channel khác
- Deploy được ở mọi nơi: Local, Self-hosted (Docker), Serverless (AWS Lambda, Vercel)
- Hỗ trợ Python và JavaScript/TypeScript SDK

### Non-Goals
- Không phải CI/CD replacement hoàn chỉnh
- Không hỗ trợ real-time collaboration (nhiều users cùng edit một task)
- Không có built-in billing/payment system

---

## 3. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Web UI   │  │ Telegram │  │ REST API │  │ JS/Python SDKs     │  │
│  │(Next.js) │  │   Bot    │  │          │  │ (embedded library) │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────────┬──────────┘  │
└───────┼─────────────┼─────────────┼───────────────────┼─────────────┘
        │             │             │                   │
        └─────────────┴──────┬──────┴───────────────────┘
                             │
                    ┌────────▼────────┐
                    │  API Gateway   │
                    │  (REST + WS)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Orchestrator   │
                    │  (Task Router) │
                    └────────┬────────┘
                             │
    ┌───────────┬────────────┼────────────┬───────────┐
    │           │            │            │           │
┌───▼───┐  ┌───▼────┐  ┌────▼────┐  ┌───▼───┐  ┌───▼───┐
│ Spec  │  │ Code   │  │  Test   │  │Debug  │  │Plan   │
│Agent  │  │ Agent  │  │  Agent  │  │Agent  │  │Agent  │
└───┬───┘  └───┬────┘  └────┬────┘  └───┬───┘  └───┬───┘
    │          │            │           │          │
    └──────────┴────────────┴───────────┴──────────┘
                             │
                    ┌────────▼────────┐
                    │  Claude CLI     │
                    │  (AI Engine)   │
                    └─────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| Web UI | Command palette, forms, chat interface, Kanban board |
| Telegram Bot | Chat-based interaction, commands |
| REST API | External integrations, webhooks |
| SDKs | Python/JS libraries for embedding |
| API Gateway | Auth, rate limiting, routing |
| Orchestrator | Task queue, job scheduling, state management |
| Agent Services | Each agent type handles specific workflow |
| Claude CLI | AI execution engine |

---

## 4. UI/UX Design

### 4.1 Web UI Components

#### Command Palette (Primary)
- **Trigger**: `Cmd+K` (Mac) / `Ctrl+K` (Windows)
- **Features**:
  - Quick command input with autocomplete
  - Recent commands history
  - Project context selector
  - Keyboard navigation

#### Form-Based Interface
- **For**: Complex tasks requiring structured input
- **Fields**: Project, Task Type, Description, Attachments, Priority
- **Validation**: Real-time validation, inline errors

#### Chat Interface
- **For**: Iterative conversations with AI
- **Features**: Markdown rendering, code syntax highlighting, file attachments

#### Kanban Board
- **Columns**: To Do → In Progress → Review → Done
- **Cards**: Task summary, assignee, priority, progress
- **Drag & Drop**: Move tasks between columns

### 4.2 Telegram Interface
- Commands: `/spec`, `/code`, `/test`, `/deploy`, `/debug`, `/status`
- Inline buttons for quick actions
- File/document upload support
- Progress updates via edit message

---

## 5. Data Models

### 5.1 Task

```typescript
interface Task {
  id: string;                    // UUID
  type: 'spec' | 'code' | 'test' | 'debug' | 'deploy' | 'plan';
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'urgent';

  // Input
  projectId: string;
  description: string;
  context: {
    files?: string[];
    repoUrl?: string;
    branch?: string;
    specId?: string;
  };

  // Output
  result?: {
    summary: string;
    files?: FileChange[];
    errors?: string[];
    logs?: string[];
  };

  // Metadata
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
  startedAt?: Date;
  completedAt?: Date;

  // Channels
  channels: {
    telegram?: { chatId: string; messageId: string };
    web?: { sessionId: string };
  };
}
```

### 5.2 Project

```typescript
interface Project {
  id: string;
  name: string;
  repoUrl: string;
  defaultBranch: string;
  techStack: string[];
  settings: {
    autoApproveSpecs: boolean;
    maxConcurrentTasks: number;
    notificationChannels: string[];
  };
  members: ProjectMember[];
}
```

### 5.3 User

```typescript
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'developer' | 'viewer';
  preferences: {
    defaultChannel: 'web' | 'telegram';
    theme: 'light' | 'dark' | 'system';
    notifications: boolean;
  };
  apiKeys: ApiKey[];
}
```

---

## 6. API Design

### 6.1 REST Endpoints

#### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tasks` | Create new task |
| GET | `/api/v1/tasks` | List tasks (with filters) |
| GET | `/api/v1/tasks/:id` | Get task details |
| DELETE | `/api/v1/tasks/:id` | Cancel/delete task |
| POST | `/api/v1/tasks/:id/approve` | Approve task output |

#### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/:id` | Get project details |
| PUT | `/api/v1/projects/:id` | Update project |
| DELETE | `/api/v1/projects/:id` | Delete project |

#### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/webhooks` | Register webhook |
| GET | `/api/v1/webhooks` | List webhooks |
| DELETE | `/api/v1/webhooks/:id` | Delete webhook |

### 6.2 WebSocket Events

```typescript
// Server → Client
interface WSEvents {
  'task:created': Task;
  'task:updated': Task;
  'task:completed': Task;
  'task:failed': { task: Task; error: string };
  'task:output': { taskId: string; chunk: string };
}

// Client → Server
interface WSCommands {
  'task:subscribe': { taskIds: string[] };
  'task:input': { taskId: string; input: string };
}
```

---

## 7. SDK Design

### 7.1 Python SDK

```python
from claudebot import ClaudeDevBot

# Initialize
bot = ClaudeDevBot(
    api_key="your-api-key",
    base_url="http://localhost:8000"
)

# Create a task
task = await bot.create_task(
    type="code",
    project_id="my-project",
    description="Add user authentication",
    context={"files": ["src/app.py"]}
)

# Get result
result = await task.wait()
print(result.summary)
```

### 7.2 JavaScript/TypeScript SDK

```typescript
import { ClaudeDevBot } from '@claudebot/sdk';

// Initialize
const bot = new ClaudeDevBot({
  apiKey: 'your-api-key',
  baseUrl: 'http://localhost:8000'
});

// Create a task
const task = await bot.createTask({
  type: 'code',
  projectId: 'my-project',
  description: 'Add user authentication',
  context: { files: ['src/app.ts'] }
});

// Stream progress
task.on('output', (chunk) => {
  console.log(chunk);
});

const result = await task.wait();
console.log(result.summary);
```

---

## 8. Deployment Architecture

### 8.1 Development (Local)

```yaml
# docker-compose.local.yaml
services:
  api:
    image: claudebot/api:latest
    ports:
      - "8000:8000"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DATABASE_URL=sqlite:///./dev.db

  web:
    image: claudebot/web:latest
    ports:
      - "3000:3000"
    depends_on:
      - api
```

### 8.2 Production (Serverless)

```
┌─────────────────────────────────────────────┐
│  AWS API Gateway / Vercel                  │
├─────────────┬─────────────┬────────────────┤
│  /api/tasks │ /api/proj   │ /api/webhooks  │
│  (Lambda)   │ (Lambda)    │ (Lambda)       │
├─────────────┴─────────────┴────────────────┤
│  Task Queue (SQS)                           │
├─────────────┬─────────────┬────────────────┤
│  spec-agent │ code-agent │ test-agent     │
│  (Lambda)   │ (Lambda)    │ (Lambda)       │
├─────────────┴─────────────┴────────────────┤
│  DynamoDB (state) + S3 (artifacts)          │
└─────────────────────────────────────────────┘
```

### 8.3 Production (Container)

```yaml
# docker-compose.prod.yaml
services:
  api:
    image: claudebot/api:${VERSION}
    deploy:
      replicas: 3
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...

  agent-executor:
    image: claudebot/agent:${VERSION}
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    deploy:
      replicas: 5

  web:
    image: claudebot/web:${VERSION}
    ports:
      - "80:80"

  telegram-bot:
    image: claudebot/telegram:${VERSION}
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
```

---

## 9. Error Handling

### Error Types

```typescript
enum ErrorCode {
  // Authentication/Authorization
  UNAUTHORIZED = 'AUTH_001',
  FORBIDDEN = 'AUTH_002',
  INVALID_API_KEY = 'AUTH_003',
  TOKEN_EXPIRED = 'AUTH_004',

  // Task Errors
  TASK_NOT_FOUND = 'TASK_001',
  TASK_CANCELLED = 'TASK_002',
  TASK_TIMEOUT = 'TASK_003',
  TASK_FAILED = 'TASK_004',

  // Agent Errors
  AGENT_UNAVAILABLE = 'AGENT_001',
  AGENT_TIMEOUT = 'AGENT_002',
  AGENT_ERROR = 'AGENT_003',

  // Claude CLI Errors
  CLAUDE_NOT_FOUND = 'Claude_001',
  CLAUDE_ERROR = 'CLAUDE_002',
  CLAUDE_TIMEOUT = 'CLAUDE_003',

  // Rate Limiting
  RATE_LIMIT_EXCEEDED = 'RATE_001',
  QUOTA_EXCEEDED = 'RATE_002',
}

interface APIError {
  code: ErrorCode;
  message: string;
  details?: Record<string, unknown>;
  requestId: string;
  timestamp: string;
}
```

### Retry Policy
- **Transient errors**: Retry 3 times with exponential backoff (1s, 2s, 4s)
- **Agent failures**: Retry once after 30 seconds
- **Claude CLI errors**: Retry with fresh session

---

## 10. Logging & Monitoring

### Log Levels
| Level | Usage |
|-------|-------|
| ERROR | Exceptions, failures, invalid inputs |
| WARN | Deprecated usage, rate limit warnings |
| INFO | Task created/completed, user actions |
| DEBUG | Request/response details, agent steps |

### Key Metrics
- **Task Metrics**: Created, Running, Completed, Failed, Duration (p50, p95, p99)
- **Agent Metrics**: Success rate, error rate, queue depth
- **System Metrics**: CPU, Memory, API latency, WebSocket connections

### Observability Stack
- **Logging**: Structured JSON logs ( Pino for Node.js, structlog for Python)
- **Metrics**: Prometheus + Grafana dashboard
- **Tracing**: OpenTelemetry with Jaeger
- **Alerting**: PagerDuty / Slack notifications

---

## 11. Security

### Authentication

| Method | Use Case | Token Lifetime |
|--------|----------|----------------|
| API Key | SDK integrations | Long-lived (1 year) |
| JWT Access Token | Web UI sessions | 15 minutes |
| JWT Refresh Token | Token rotation | 7 days |
| Telegram Bot Auth | Telegram commands | Per-session |

**JWT Structure:**
```typescript
interface JWTPayload {
  sub: string;        // userId
  role: 'admin' | 'developer' | 'viewer';
  projects: string[]; // accessible project IDs
  iat: number;
  exp: number;
}
```

### Authorization (RBAC)

| Permission | Admin | Developer | Viewer |
|------------|-------|-----------|--------|
| Create Task | ✅ | ✅ | ❌ |
| View Task | ✅ (all) | ✅ (own projects) | ✅ (own projects) |
| Cancel Task | ✅ | ✅ (own) | ❌ |
| Approve Output | ✅ | ✅ | ❌ |
| Manage Projects | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ❌ | ❌ |
| Manage Webhooks | ✅ | ✅ | ❌ |

### Rate Limiting

| Plan | Requests/min | Concurrent Tasks | Max Duration |
|------|--------------|------------------|--------------|
| Free | 10 | 2 | 5 min |
| Pro | 60 | 10 | 15 min |
| Enterprise | Unlimited | Unlimited | 30 min |

### API Key Scopes

```typescript
interface ApiKey {
  id: string;
  name: string;
  scopes: ('tasks:read' | 'tasks:write' | 'projects:read' | 'projects:write')[];
  projectId?: string; // If scoped to single project
  createdAt: Date;
  expiresAt?: Date;
}
```

---

## 12. Implementation Phases

### Phase 1: Core API (Week 1-2)
**Goal:** Functional API server with basic task execution

| Deliverable | Description |
|-------------|-------------|
| REST API Server | FastAPI/Express server with `/api/v1/tasks` endpoints |
| Task Model | Database schema for Task, Project, User |
| SQLite Database | Local development database |
| Task Queue | Redis-based queue for async task processing |
| Code Agent | Basic code generation using Claude CLI |
| CLI Integration | Wrapper for Claude Code CLI invocation |

**Deliverables Checklist:**
- [ ] `POST /api/v1/tasks` returns task ID
- [ ] `GET /api/v1/tasks/:id` returns task status
- [ ] Task status transitions: pending → queued → running → completed/failed
- [ ] Claude CLI invoked with task description
- [ ] Result stored and returned to client

### Phase 2: Multi-Channel (Week 3-4)
**Goal:** Web UI and Telegram integration with real-time updates

| Deliverable | Description |
|-------------|-------------|
| Web UI | Next.js frontend with command palette |
| Telegram Bot | Python-telegram-bot integration |
| WebSocket | Real-time task progress streaming |
| Channel Sync | Unified task state across channels |

**Deliverables Checklist:**
- [ ] Web UI: Cmd+K opens command palette
- [ ] Web UI: Tasks list with status
- [ ] Telegram: `/code`, `/spec`, `/test` commands work
- [ ] WebSocket: Task progress streams to UI
- [ ] Task created in Telegram visible in Web UI

### Phase 3: SDKs (Week 5-6)
**Goal:** Python and JavaScript SDKs for external integrations

| Deliverable | Description |
|-------------|-------------|
| Python SDK | pip-installable package |
| JS SDK | npm package `@claudebot/sdk` |
| SDK Docs | Usage examples, API reference |

**Deliverables Checklist:**
- [ ] `pip install claudebot` works
- [ ] `npm install @claudebot/sdk` works
- [ ] SDKs can create tasks and stream results
- [ ] TypeScript types complete

### Phase 4: Production Ready (Week 7-8)
**Goal:** Production deployment options with monitoring

| Deliverable | Description |
|-------------|-------------|
| PostgreSQL | Production database with migrations |
| Redis | Production queue and session storage |
| Docker | Multi-container compose files |
| Serverless | AWS Lambda / Vercel templates |
| Monitoring | Prometheus metrics, Grafana dashboard |
| Alerting | Error alerts to Slack |

**Deliverables Checklist:**
- [ ] Docker Compose production stack works
- [ ] Serverless deployment under 10 minutes
- [ ] Grafana shows task metrics
- [ ] Errors trigger Slack alerts

---

## 13. Acceptance Criteria

1. **Task Creation**: User có thể tạo task qua REST API và nhận task ID
2. **Agent Execution**: Task được xử lý bởi đúng agent và trả về kết quả
3. **Multi-Channel Sync**: Task tạo ở Telegram có thể xem progress ở Web UI
4. **SDK可用性**: Python và JS SDK có thể import và sử dụng được
5. **Deployment**: Có thể deploy local với Docker Compose trong 5 phút

---

## 14. Open Questions & Decisions

### Resolved Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Claude API Key Management | Organization-level (shared) | Simpler for teams, reduce per-user complexity |
| Storage for Artifacts | S3-compatible (local filesystem for dev) | Production uses S3, dev uses local |
| Max Execution Time | 15 minutes | Balance between flexibility and resource management |
| Pricing Model | Per-project subscription | Predictable billing for teams |

### Future Considerations (Post-MVP)
- Per-user API keys with usage tracking
- Usage-based pricing for high-volume teams
- Enterprise self-hosted option with unlimited execution

---

*Document Version: 1.0*
*Last Updated: 2026-03-16*

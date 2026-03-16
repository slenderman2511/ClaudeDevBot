# ClaudeDevBot Embedded Library - Design Specification

**Date:** 2026-03-16
**Topic:** Embedded Library - Multi-Channel AI Development Assistant
**Status:** Draft

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

## 9. Security

### Authentication
- API Keys for SDKs and external integrations
- JWT tokens for Web UI sessions
- Telegram login via Bot API

### Authorization
- Role-based access control (RBAC)
- Project-level permissions
- API key scopes

### Rate Limiting
- Per-user rate limits
- Per-project rate limits
- Queue-based priority for paid plans

---

## 10. Implementation Phases

### Phase 1: Core API
- [ ] API server với REST endpoints
- [ ] Task queue system
- [ ] Basic agent execution (code agent)
- [ ] SQLite database

### Phase 2: Multi-Channel
- [ ] Web UI (command palette + forms)
- [ ] Telegram bot integration
- [ ] WebSocket real-time updates

### Phase 3: SDKs
- [ ] Python SDK
- [ ] JavaScript/TypeScript SDK
- [ ] Documentation & examples

### Phase 4: Production Ready
- [ ] PostgreSQL + Redis
- [ ] Docker deployment
- [ ] Serverless templates
- [ ] Monitoring & logging

---

## 11. Acceptance Criteria

1. **Task Creation**: User có thể tạo task qua REST API và nhận task ID
2. **Agent Execution**: Task được xử lý bởi đúng agent và trả về kết quả
3. **Multi-Channel Sync**: Task tạo ở Telegram có thể xem progress ở Web UI
4. **SDK可用性**: Python và JS SDK có thể import và sử dụng được
5. **Deployment**: Có thể deploy local với Docker Compose trong 5 phút

---

## 12. Open Questions

- [ ] Claude API key management: Per-user hay organization-level?
- [ ] Storage cho artifacts: S3-compatible hay local filesystem?
- [ ] Max execution time cho tasks: 5 min, 15 min, hay unlimited?
- [ ] Pricing model: Per-task, per-user, hay subscription?

---

*Document Version: 1.0*
*Last Updated: 2026-03-16*

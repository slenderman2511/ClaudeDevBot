# ClaudeDevBot Plugin - Design Specification

**Date:** 2026-03-17
**Topic:** ClaudeDevBot Plugin - Injectable AI Development Assistant
**Status:** Pending Review (v2)

---

## 1. Executive Summary

Thiết kế plugin ClaudeDevBot có thể inject vào bất kỳ repository nào, cho phép developers sử dụng AI-driven workflows (Spec, Code, Test, Deploy, Debug) thông qua Telegram Bot. Plugin hoạt động như một embedded module trong project, với REST API để Telegram Bot gọi.

---

## 2. Goals & Non-Goals

### Goals
- Plugin có thể cài đặt vào bất kỳ repo nào qua `pip install`
- Cấu trúc `.claudebot/` trong repo với config và code
- Refactor từ existing ai-devbot/devbot code
- REST API để Telegram Bot remote gọi
- Hỗ trợ đầy đủ workflows: Spec, Code, Test, Deploy, Debug
- CLI commands để chạy trực tiếp trong repo

### Non-Goals
- Không tạo standalone SaaS platform
- Không hỗ trợ multi-user authentication trong plugin
- Không có built-in web UI (dùng Telegram làm interface)

---

## 3. Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER                                    │
│                         (Local Machine)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   my-repo/                                                          │
│   ├── .claudebot/           ← Plugin installed here                │
│   │   ├── config.yaml                                                │
│   │   ├── api/                                                       │
│   │   │   └── server.py        ← REST API (localhost:8765)         │
│   │   ├── agents/                                                     │
│   │   │   ├── spec_agent.py                                           │
│   │   │   ├── code_agent.py                                          │
│   │   │   ├── test_agent.py                                          │
│   │   │   ├── deploy_agent.py                                        │
│   │   │   └── debug_agent.py                                         │
│   │   ├── orchestrator/                                             │
│   │   ├── tools/                                                    │
│   │   │   ├── claude_cli.py                                          │
│   │   │   └── git_tools.py                                            │
│   │   └── cli.py                                                     │
│   ├── src/                                                          │
│   └── .claudebotrc          ← Quick config                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ REST API calls
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     TELEGRAM BOT (Remote)                          │
│                                                                     │
│   Developer → Telegram → Bot Server → http://localhost:8765/api   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `.claudebot/api/server.py` | FastAPI server, exposes REST endpoints |
| `.claudebot/agents/` | 5 agent implementations (Spec, Code, Test, Deploy, Debug) |
| `.claudebot/orchestrator/` | Task queue, job scheduling |
| `.claudebot/tools/` | Claude CLI wrapper, Git tools |
| `.claudebot/cli.py` | CLI commands for direct usage |
| `.claudebot/config.yaml` | Project-specific configuration |
| `.claudebotrc` | Quick config file |

### Orchestrator Design

The orchestrator manages task lifecycle from creation to completion.

```python
class TaskOrchestrator:
    """Manages task queue and agent execution"""

    def __init__(self, config: Config):
        self.config = config
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: dict[str, Task] = {}
        self.task_history: list[Task] = []

    async def create_task(self, request: CreateTaskRequest) -> Task:
        """Create and queue a new task"""
        task = Task(
            id=uuid4(),
            type=request.type,
            status=TaskStatus.PENDING,
            description=request.description,
            files=request.files,
            branch=request.branch,
            priority=request.priority,
            created_at=datetime.now()
        )
        await self.queue.put(task)
        return task

    async def run(self):
        """Main loop - processes queued tasks"""
        while True:
            task = await self.queue.get()
            await self._execute_task(task)
            self.queue.task_done()

    async def _execute_task(self, task: Task):
        """Execute a single task with the appropriate agent"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task.id] = task

        try:
            agent = self._get_agent(task.type)
            context = AgentContext(
                repo_path=self.config.repo_path,
                branch=task.branch,
                claude_api_key=os.environ["CLAUDE_API_KEY"],
                config=self.config.agent_config
            )

            result = await agent.execute(task, context)

            task.status = TaskStatus.COMPLETED
            task.result = result.__dict__

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        finally:
            task.completed_at = datetime.now()
            del self.running_tasks[task.id]
            self.task_history.append(task)

    def _get_agent(self, task_type: TaskType) -> BaseAgent:
        """Get agent instance for task type"""
        # Load from config - which agents are enabled
        pass
```

**Task Queue Implementation:**
- **Development**: In-memory `asyncio.Queue`
- **Production**: Redis-based queue (future enhancement)

---

## 4. Installation

### Option A: pip install

```bash
# Install package
pip install claudebot

# Initialize in repo
claudebot init
```

### Option B: Clone template

```bash
# Clone into existing repo
git clone https://github.com/claudebot/plugin-template.git .claudebot/

# Or use degit
npx degit claudebot/plugin-template .claudebot
```

### Directory Structure After Init

```
my-repo/
├── .claudebot/
│   ├── __init__.py
│   ├── config.yaml          # Generated from template
│   ├── requirements.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py       # FastAPI server
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── tasks.py
│   │       └── agents.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── spec_agent.py
│   │   ├── code_agent.py
│   │   ├── test_agent.py
│   │   ├── deploy_agent.py
│   │   └── debug_agent.py
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── task_manager.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── claude_cli.py
│   │   └── git_tools.py
│   ├── cli.py               # CLI entry point
│   └── pyproject.toml
├── .claudebotrc            # Quick: port = 8765, agents = all
├── src/
└── ...
```

---

## 5. Data Models

### 5.1 Config

```yaml
# .claudebot/config.yaml
server:
  host: "localhost"
  port: 8765

agents:
  enabled:
    - spec
    - code
    - test
    - deploy
    - debug
  timeout: 300  # seconds

claude:
  model: "claude-3-5-sonnet-20241022"
  # API key loaded from environment: CLAUDE_API_KEY

git:
  auto_commit: false
  default_branch: "main"

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  allowed_users: []  # Empty = allow all
```

**Config Precedence:**
1. `.claudebot/config.yaml` - Full configuration (YAML)
2. `.claudebotrc` - Quick overrides (INI)
3. Environment variables - Highest priority

For most projects, `.claudebot/config.yaml` is sufficient. `.claudebotrc` is for quick CLI overrides.

### 5.2 Task

```python
from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime

class TaskType(str, Enum):
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    DEPLOY = "deploy"
    DEBUG = "debug"

class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str  # UUID
    type: TaskType
    status: TaskStatus
    description: str

    # Context
    repo_path: str
    branch: Optional[str] = None
    files: list[str] = []

    # Result
    result: Optional[dict] = None
    error: Optional[str] = None
    logs: list[str] = []

    # Metadata
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

---

## 6. API Design

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create new task |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Get task details |
| DELETE | `/api/tasks/{id}` | Cancel task |
| POST | `/api/tasks/{id}/cancel` | Cancel running task |
| GET | `/api/agents` | List available agents |
| GET | `/api/health` | Health check |
| POST | `/api/webhook/telegram` | Telegram webhook |

### Request/Response Schemas

```python
# POST /api/tasks - Create Task
class CreateTaskRequest(BaseModel):
    type: TaskType  # spec, code, test, deploy, debug
    description: str
    files: list[str] = []
    branch: str = "main"
    priority: int = 0  # Higher = more urgent

class CreateTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime

# GET /api/tasks/{id} - Get Task
class TaskDetailResponse(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    result: Optional[dict] = None
    error: Optional[str] = None
    logs: list[str] = []
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# GET /api/agents - List Agents
class AgentInfo(BaseModel):
    name: str
    description: str
    enabled: bool

class ListAgentsResponse(BaseModel):
    agents: list[AgentInfo]

# GET /api/health - Health Check
class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded"
    version: str
    agents_available: list[str]
```

### Authentication

| Scenario | Method |
|----------|--------|
| Local CLI → API | No auth (localhost) |
| Telegram Bot → API | API Key in header: `X-API-Key: <token>` |
| Webhook verification | HMAC signature in `X-Telegram-Signature` header |

**API Key Configuration:**
```yaml
# .claudebot/config.yaml
server:
  api_key: "your-secret-api-key"  # Generate with: claudebot config generate-key
```

### Rate Limiting

- Default: 60 requests/minute
- Configurable via `config.yaml`:
```yaml
server:
  rate_limit: 60  # requests per minute
```

### WebSocket (Optional)

```python
# For real-time progress
ws = WebSocket()
await ws.connect("ws://localhost:8765/ws/tasks/{task_id}")

# Events:
# - task:started
# - task:progress
# - task:completed
# - task:failed
```

---

## 7. Agent Design

### Base Agent Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentContext:
    """Context passed to all agents - provides access to tools and project state"""
    repo_path: str
    branch: str
    claude_api_key: str
    config: dict

@dataclass
class AgentResult:
    """Standard result from any agent"""
    success: bool
    summary: str
    files_created: list[str] = []
    files_modified: list[str] = []
    logs: list[str] = []
    error: Optional[str] = None

class BaseAgent(ABC):
    name: str
    description: str

    @abstractmethod
    async def execute(self, task: Task, context: AgentContext) -> AgentResult:
        """Execute the agent task. Returns result with files and logs."""
        pass

    @abstractmethod
    def validate_input(self, task: Task) -> tuple[bool, Optional[str]]:
        """Validate task input. Returns (is_valid, error_message)"""
        pass

    def get_required_files(self, task: Task) -> list[str]:
        """Return list of files agent needs to read"""
        return []

    async def on_error(self, error: Exception, task: Task) -> AgentResult:
        """Handle errors - can be overridden for custom recovery"""
        return AgentResult(
            success=False,
            summary=f"Error: {str(error)}",
            error=str(error)
        )
```

### Tools Available to Agents

```python
class AgentTools:
    """Tools available to all agents"""

    def __init__(self, context: AgentContext):
        self.context = context

    async def read_file(self, path: str) -> str:
        """Read file contents"""

    async def write_file(self, path: str, content: str) -> None:
        """Write file contents"""

    async def list_files(self, pattern: str = "**/*") -> list[str]:
        """List files matching pattern"""

    async def run_command(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Run shell command"""

    async def call_claude(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Claude CLI/API"""

    async def git(self, *args) -> str:
        """Run git command"""

    def log(self, message: str, level: str = "info") -> None:
        """Add log entry"""
```

### Agent Implementations

| Agent | Input | Output |
|-------|-------|--------|
| Spec Agent | Description, existing files | SPEC.md content |
| Code Agent | Spec/description, target files | Modified files |
| Test Agent | Code files, test requirements | Test files |
| Deploy Agent | Deployment config | Deployment commands/script |
| Debug Agent | Error logs, code | Suggested fixes |

---

## 8. CLI Commands

```bash
# Start API server
claudebot serve
# or
python -m claudebot serve --port 8765

# Run a task directly
claudebot run code "Add user authentication"
claudebot run spec "Create API specification"
claudebot run test "Add unit tests for user model"

# List tasks
claudebot tasks list
claudebot tasks status <task_id>

# Cancel task
claudebot tasks cancel <task_id>

# Config
claudebot config show
claudebot config set agents.code true

# Init new project
claudebot init
```

---

## 9. Telegram Integration

### Setup

1. Create Telegram Bot via @BotFather
2. Set webhook: `https://your-server.com/api/webhook/telegram`
3. Configure bot token in `.claudebot/config.yaml`

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show available commands |
| `/code <description>` | Generate code |
| `/spec <description>` | Generate spec |
| `/test <description>` | Generate tests |
| `/debug <error>` | Debug error |
| `/status` | Check task status |
| `/cancel <task_id>` | Cancel task |

### Bot ↔ Plugin Communication

```
Telegram User
    │
    ▼
Telegram Bot Server (remote)
    │ POST /api/tasks
    ▼
Plugin API (localhost:8765)
    │
    ▼
Orchestrator → Agent → Claude CLI
    │
    ▼
Response back via Webhook
```

---

## 10. Refactoring from Existing Code

### Reuse Strategy

| Existing Code | Reuse in Plugin |
|---------------|-----------------|
| `ai-devbot/agents/*.py` | Core agent logic |
| `ai-devbot/tools/claude_cli.py` | Claude CLI wrapper |
| `ai-devbot/tools/git_tools.py` | Git operations |
| `ai-devbot/workflows/orchestration.py` | Task orchestration |
| `ai-devbot/bot/telegram_bot.py` | Reference for Telegram integration |
| `devbot/cli/commands/*.py` | CLI commands |

### Architecture Changes

1. **Extract** agent logic thành reusable modules
2. **Wrap** trong FastAPI server
3. **Add** REST endpoints
4. **Create** CLI wrapper
5. **Package** thành installable module

---

## 11. Implementation Phases

### Phase 1: Core Plugin Structure (Week 1)
- [ ] Create `.claudebot/` directory structure
- [ ] Setup FastAPI server with basic routes
- [ ] Create base agent class
- [ ] Implement Code Agent (reuse from ai-devbot)
- [ ] CLI commands: `serve`, `run`

### Phase 2: Remaining Agents (Week 2)
- [ ] Implement Spec Agent
- [ ] Implement Test Agent
- [ ] Implement Deploy Agent
- [ ] Implement Debug Agent
- [ ] Task queue system

### Phase 3: Telegram Integration (Week 3)
- [ ] Setup Telegram webhook handler
- [ ] Command routing
- [ ] Response formatting
- [ ] Task status updates

### Phase 4: Polish & Package (Week 4)
- [ ] CLI improvements
- [ ] Configuration system
- [ ] Package for PyPI
- [ ] Documentation

---

## 12. Acceptance Criteria

1. **Installation**: `pip install claudebot && claudebot init` works
2. **API Server**: `claudebot serve` starts REST API on configured port
3. **Task Execution**: POST to `/api/tasks` triggers agent and returns result
4. **CLI**: `claudebot run code "task"` works directly
5. **Telegram**: Bot can call plugin API and get responses
6. **Reuse**: Code from ai-devbot/devbot reused where possible
7. **Config**: Project-specific config in `.claudebot/config.yaml`

---

## 13. Resolved Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Multi-project handling | One plugin per repo | Each repo has own `.claudebot/`, run on different ports |
| API security | API Key auth | Header `X-API-Key` required for non-localhost requests |
| Task persistence | SQLite (local) | Simple, file-based, sufficient for single-user |
| Claude API key | Environment variable | Use `CLAUDE_API_KEY` env var, allow per-project via `.env` |

### Multi-Project Setup Example

```bash
# Project A
cd project-a
claudebot serve --port 8765

# Project B (different terminal)
cd project-b
claudebot serve --port 8766

# Configure Telegram bot to know which port each project uses
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_API_KEY` | Yes | Claude API key |
| `TELEGRAM_BOT_TOKEN` | No | For Telegram integration |
| `CLAUDEBOT_API_KEY` | No | For remote API access |
| `CLAUDEBOT_PORT` | No | Override default port (8765) |

---

## 14. Future Enhancements (Post-MVP)

- Redis queue for production deployments
- PostgreSQL for multi-user support
- WebSocket for real-time progress
- Plugin marketplace with community agents

---

*Document Version: 1.0*
*Last Updated: 2026-03-17*

# ClaudeDevBot Plugin - Design Specification

**Date:** 2026-03-17
**Topic:** ClaudeDevBot Plugin - Injectable AI Development Assistant
**Status:** Draft

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

```ini
# .claudebotrc (alternative simple config)
[server]
port = 8765

[agents]
enabled = spec,code,test,deploy,debug

[claude]
model = claude-3-5-sonnet-20241022
```

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

class BaseAgent(ABC):
    name: str
    description: str

    @abstractmethod
    async def execute(self, task: Task) -> Task:
        """Execute the agent task. Returns updated task with result."""
        pass

    @abstractmethod
    def validate_input(self, task: Task) -> bool:
        """Validate task input before execution."""
        pass
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

## 13. Open Questions

- [ ] How to handle multiple projects on same machine?
- [ ] How to secure API when called from remote Telegram bot?
- [ ] How to persist task history across restarts?
- [ ] How to handle Claude API key per-project vs. global?

---

*Document Version: 1.0*
*Last Updated: 2026-03-17*

# AI DevBot - Architecture Specification

## System Overview

AI DevBot is a modular multi-agent system that processes developer commands from Telegram and orchestrates AI agents to execute engineering workflows.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM INTERFACE                        │
│                   (telegram_bot.py)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  COMMAND ROUTING LAYER                       │
│              (command_router.py)                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              WORKFLOW ORCHESTRATION LAYER                    │
│     (orchestration.py, task_planner.py)                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ SPEC AGENT  │  │  CODE AGENT │  │  TEST AGENT │
     └─────────────┘  └─────────────┘  └─────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
     ┌─────────────────────────────────────────────────────┐
     │                   TOOLS LAYER                       │
     │   (claude_cli.py, telegram_api.py, git_tools.py)   │
     └─────────────────────────────────────────────────────┘
                              │
     ┌─────────────┬─────────────┬─────────────┬─────────────┐
     │             │             │             │             │
     ▼             ▼             ▼             ▼             ▼
  ┌──────┐    ┌──────┐     ┌──────┐     ┌──────┐      ┌──────┐
  │ CONF │    │MEMORY│     │ OBSER│     │GUARD │      │ TESTS│
  │      │    │      │     │VABILI│     │RAILS │      │      │
  └──────┘    └──────┘     └──────┘     └──────┘      └──────┘
```

---

## Layer Definitions

### 1. Configuration Layer (`config/`)

Centralized configuration management using YAML with environment variable substitution.

**Files:**
- `config.yaml` - Main configuration file

**Responsibilities:**
- Bot credentials
- Agent parameters
- Memory settings
- Observability config
- Guardrails rules

---

### 2. Data and Memory Layer (`data/`)

Manages conversation history and persistent knowledge.

**Components:**
- **Short-term Memory:** In-memory cache with TTL
- **Long-term Memory:** Persistent storage with embeddings

**Files:**
- `data/memory/short_term/` - Ephemeral task data
- `data/memory/long_term/` - Persistent knowledge base

---

### 3. Agent Layer (`agents/`)

Base classes and specialized agents for different tasks.

**BaseAgent Abstract Class:**
```python
class BaseAgent(ABC):
    - name: str
    - model: str
    - max_iterations: int
    - timeout: int
    + execute(task: Task) -> AgentResult
    + validate_input(input: str) -> bool
    + get_capabilities() -> List[str]
```

**Specialized Agents:**
| Agent | Purpose | Key Methods |
|-------|---------|-------------|
| SpecAgent | Generate specifications | `generate_spec(requirements)` |
| CodeAgent | Write implementation code | `write_code(spec)` |
| TestAgent | Execute and generate tests | `run_tests(scope)` |
| DeployAgent | Handle deployments | `deploy(target)` |
| DebugAgent | Analyze and fix issues | `debug(error)` |

---

### 4. Tools Layer (`tools/`)

Abstraction for external services and CLI operations.

**Tool Interface:**
```python
class Tool(ABC):
    - name: str
    - description: str
    + execute(**kwargs) -> ToolResult
    + validate() -> bool
```

**Implemented Tools:**
| Tool | Purpose |
|------|---------|
| claude_cli.py | Claude Code CLI wrapper |
| telegram_api.py | Telegram Bot API client |
| git_tools.py | Git operations wrapper |

---

### 5. Workflow Orchestration Layer (`workflows/`)

Coordinates agent execution and task management.

**Components:**
- **Command Router:** Parses and routes Telegram commands
- **Orchestration:** Manages multi-agent workflows
- **Task Planner:** Creates execution plans

**Flow:**
```
Command → Router → Task Planner → Orchestration → Agent(s) → Tools → Result
```

---

### 6. Observability Layer (`observability/`)

Monitoring, logging, and tracing.

**Components:**
- `logging.py` - Structured JSON logging
- `tracing.py` - Distributed tracing
- `metrics.py` - Prometheus metrics

---

### 7. Guardrails Layer (`guardrails/`)

Security and validation checks.

**Components:**
- `permissions.py` - User permission management
- `command_validation.py` - Input sanitization and validation

---

### 8. Tests (`tests/`)

Unit and integration tests.

**Coverage:**
- Agent behavior
- Workflow orchestration
- Command routing
- Guardrails validation

---

## Data Flow

1. **Incoming Command:** Telegram message received by bot
2. **Validation:** Guardrails check command validity
3. **Routing:** CommandRouter maps command to agent
4. **Planning:** TaskPlanner creates execution steps
5. **Execution:** Orchestrator coordinates agent execution
6. **Tools:** Agents use tools to perform actions
7. **Memory:** Results stored in appropriate memory layer
8. **Response:** Bot sends result back to user
9. **Observability:** All steps logged and traced

---

## Extension Points

- Add new agents by extending `BaseAgent`
- Add new tools by implementing `Tool` interface
- Add new guards in `guardrails/`
- Add new workflows in `workflows/`

---

## Error Handling

- Retry with exponential backoff for transient failures
- Circuit breaker for failing tools
- Dead letter queue for failed tasks
- User-friendly error messages

---

## Security Considerations

- Environment variable secrets
- User allowlist for bot access
- Command input validation
- Rate limiting per user
- Audit logging for all operations

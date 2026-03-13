# DevBot Architecture

This document describes the architecture of DevBot, an AI engineering teammate that provides spec-driven development using OpenSpec and Claude Code.

## System Overview

DevBot follows a modular, component-based architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Interface                          │
│                 (devbot_cli.py - Click)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Module                             │
│                  (devbot_core.py)                          │
│  - attach()  - scan()  - build_graph()                  │
│  - create_feature()  - plan_feature()  - implement()     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Scanner     │  │    Graph      │  │    Spec      │
│  Project      │  │    Code       │  │    OpenSpec  │
│  Stack        │  │    Graph      │  │    Sync      │
│  Detection    │  │  Builder      │  │    Generator │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agents                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │
│  │ Planner │ │  Code   │ │  Test   │ │   Deploy    │  │
│  │ Agent   │ │  Agent  │ │  Agent  │ │   Agent     │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Orchestrator                             │
│            TaskGraph + Executor (Async)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tools                                │
│        Claude CLI        │        Git Tools               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. CLI Layer (`cli/`)

The CLI layer uses Click to provide a command-line interface.

**Files:**
- `devbot_cli.py` - Main CLI commands

**Commands:**
- `attach` - Initialize DevBot in a project
- `scan` - Detect tech stack
- `graph` - Build code knowledge graph
- `feature` - Create feature specification
- `plan` - Generate task plan
- `implement` - Execute feature implementation
- `status` - Show DevBot status
- `list` - List features

### 2. Core Layer (`core/`)

The core layer orchestrates all components.

**Files:**
- `devbot_core.py` - Main DevBot class

**Responsibilities:**
- Initialize all components
- Coordinate workflow between modules
- Manage project state
- Provide high-level API

### 3. Scanner Layer (`scanner/`)

Analyzes project structure and detects technology stack.

**Modules:**

#### ProjectScanner
- Scans directory structure
- Detects programming languages
- Finds dependencies
- Identifies test files
- Lists configuration files

#### StackDetector
- Detects frameworks (Django, Flask, React, etc.)
- Identifies libraries
- Detects databases (PostgreSQL, MySQL, MongoDB, etc.)
- Identifies tools (pytest, Docker, etc.)

### 4. Graph Layer (`graph/`)

Builds a semantic knowledge graph of the codebase.

**Modules:**

#### CodeGraphBuilder
- Parses source files
- Extracts classes, functions, imports
- Builds nodes (files, classes, functions)
- Creates edges (imports, calls, dependencies)

#### SymbolParser
- Parses Python AST
- Extracts function signatures
- Extracts class definitions
- Extracts imports

### 5. Spec Layer (`spec/`)

Manages OpenSpec feature specifications.

**Modules:**

#### OpenSpecSync
- Load/save feature specs
- Parse markdown specifications
- Track task completion
- Generate task graphs
- Validate specifications

#### SpecGenerator
- Generate specs using AI
- Create markdown content
- Define tasks and phases

### 6. Agents Layer (`agents/`)

AI agents for different tasks.

**Modules:**

#### BaseAgent
- Abstract base class
- Task execution interface
- Input validation
- Result formatting

#### PlannerAgent
- Analyzes feature specifications
- Creates task DAGs
- Determines task dependencies
- Optimizes execution order

#### CodeAgent
- Generates implementation code
- Uses Claude Code CLI
- Integrates with OpenSpec
- Supports multiple languages

#### TestAgent
- Runs pytest tests
- Generates test cases
- Reports results

#### DeployAgent
- Deploys to various platforms
- Vercel, Docker, Heroku support
- Deployment planning

### 7. Orchestrator Layer (`orchestrator/`)

Manages task execution.

**Modules:**

#### TaskGraph
- Directed Acyclic Graph (DAG) of tasks
- Task state management
- Dependency resolution
- Topological sorting for parallel execution

#### Executor
- Async task execution
- Parallel execution within levels
- Retry logic
- Progress tracking
- Agent pool management

### 8. Tools Layer (`tools/`)

External tool integrations.

**Modules:**

#### Tool (Base)
- Abstract base class
- Execute interface
- Schema generation

#### ClaudeCLITool
- Execute Claude Code commands
- Non-interactive mode
- Session management
- Model configuration

#### GitTool
- Repository operations
- Branch management
- Commit/push/pull
- Diff generation

#### ToolRegistry
- Central tool registration
- Tool lookup
- Schema aggregation

### 9. Integrations Layer (`integrations/`)

External service integrations.

**Modules:**

#### DevBotTelegramBot
- Telegram bot interface
- Command handlers
- Remote DevBot control

### 10. Memory Layer (`memory/`)

Context management.

**Modules:**

#### ShortTermMemory
- In-memory cache with TTL
- Thread-safe operations
- Auto-eviction

#### LongTermMemory
- File-based persistence
- Search functionality
- Index management

#### Memory
- Unified interface
- Short + Long term combination

### 11. Observability Layer (`observability/`)

Logging and tracing.

**Modules:**

#### Logger
- Structured logging
- Color support
- Context management

#### Tracing
- Operation tracking
- Span management
- Performance metrics

## Data Flow

### 1. Attach Flow

```
CLI → DevBot.attach()
  → Create .devbot directory
  → Save project_profile.json
  → Save devbot_state.json
```

### 2. Scan Flow

```
CLI → DevBot.scan()
  → ProjectScanner.scan()
    → Scan directory structure
    → Detect languages
    → Find dependencies
  → StackDetector.detect()
    → Identify frameworks
    → Detect databases
    → Find tools
  → Save to .devbot/project_profile.json
```

### 3. Feature Creation Flow

```
CLI → DevBot.create_feature()
  → SpecGenerator.generate()
    → Generate tasks
    → Create markdown content
  → OpenSpecSync.create_feature()
    → Save to openspec/features/
```

### 4. Planning Flow

```
CLI → DevBot.plan_feature()
  → OpenSpecSync.load_feature()
    → Parse markdown spec
  → PlannerAgent.execute()
    → Create TaskGraph
    → Topological sort
    → Generate execution levels
  → Save plan to openspec/plans/
```

### 5. Implementation Flow

```
CLI → DevBot.implement_feature()
  → OpenSpecSync.load_feature()
  → OpenSpecSync.get_pending_tasks()
  → TaskGraph.create_task_graph()
  → Executor.execute()
    → For each execution level:
      → Spawn agents (parallel)
      → Execute via Claude CLI
      → Collect results
  → Update feature tasks
```

## Configuration

### Project Structure

When attached to a project, DevBot creates:

```
project/
├── .devbot/                    # DevBot metadata
│   ├── project_profile.json   # Project scan results
│   ├── code_graph.json       # Code knowledge graph
│   └── devbot_state.json    # State tracking
├── openspec/                  # OpenSpec directory
│   ├── features/            # Feature specifications
│   │   └── payment-service.md
│   ├── context/             # Project context
│   └── plans/               # Execution plans
│       └── payment-service-plan.md
└── ... (project files)
```

### Key Classes

#### DevBot
Main entry point for all operations.

```python
class DevBot:
    def attach(self) -> Dict
    def scan(self) -> Dict
    def build_graph(self) -> Dict
    def create_feature(self, name: str, desc: str) -> Dict
    def plan_feature(self, name: str) -> Dict
    async def implement_feature(self, name: str) -> Dict
```

#### TaskGraph
Manages task execution order.

```python
class TaskGraph:
    def add_task(self, task: TaskItem)
    def calculate_execution_levels(self) -> List[List[TaskItem]]
    def get_stats(self) -> Dict
```

#### Executor
Runs tasks asynchronously.

```python
class Executor:
    def register_agent(self, agent_type: str, agent)
    async def execute(self, task_graph: TaskGraph) -> Dict
```

## Extension Points

### Adding New Agents

1. Extend `BaseAgent`
2. Implement `execute(task: Task) -> AgentResult`
3. Register with Executor:

```python
executor.register_agent('custom', CustomAgent())
```

### Adding New Tools

1. Extend `Tool` class
2. Implement `execute(**kwargs) -> ToolResult`
3. Register with ToolRegistry:

```python
registry.register(CustomTool())
```

### Adding New Integrations

1. Create module in `integrations/`
2. Implement bot/hook interface
3. Add CLI command if needed

## Error Handling

Each layer handles errors gracefully:

- **CLI**: Clicks exception handling, user-friendly messages
- **Core**: Try-catch with error dictionary returns
- **Agents**: AgentResult with success/error fields
- **Executor**: Task-level error tracking, continue on failure option

## Testing

The architecture supports:

- Unit tests for each module
- Integration tests for workflows
- Agent-specific test suites
- Mock tools for CI/CD

## Performance Considerations

- **Async I/O**: Executor uses asyncio for parallel execution
- **Caching**: OpenSpec caches loaded features
- **Lazy Loading**: Components initialized on-demand
- **Memory Management**: Short-term memory with TTL auto-cleanup

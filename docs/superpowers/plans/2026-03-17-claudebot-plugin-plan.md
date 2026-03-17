# ClaudeDevBot Plugin Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an injectable ClaudeDevBot plugin that can be installed in any repository via `pip install`, providing AI-driven development workflows (Spec, Code, Test, Deploy, Debug) through a REST API and CLI.

**Architecture:** Plugin installs to `.claudebot/` directory in target repository. REST API server runs locally (localhost:8765), called by Telegram Bot or CLI. Reuses existing agent logic from ai-devbot/devbot.

**Tech Stack:** Python, FastAPI, Pydantic, SQLite, python-telegram-bot

---

## File Structure

```
.claudebot/
├── __init__.py
├── config.yaml
├── pyproject.toml
├── requirements.txt
├── api/
│   ├── __init__.py
│   ├── server.py          # FastAPI application
│   └── routes/
│       ├── __init__.py
│       ├── tasks.py       # Task endpoints
│       └── health.py      # Health check
├── agents/
│   ├── __init__.py
│   ├── base_agent.py      # BaseAgent abstract class
│   ├── spec_agent.py
│   ├── code_agent.py
│   ├── test_agent.py
│   ├── deploy_agent.py
│   └── debug_agent.py
├── orchestrator/
│   ├── __init__.py
│   └── task_manager.py    # TaskOrchestrator
├── tools/
│   ├── __init__.py
│   ├── claude_cli.py     # Claude CLI wrapper
│   └── git_tools.py
├── cli.py                 # CLI entry point
└── db/
    ├── __init__.py
    └── models.py          # SQLite models
```

---

## Chunk 1: Project Setup & Core Structure

### Task 1: Create Project Structure

**Files:**
- Create: `.claudebot/__init__.py`
- Create: `.claudebot/pyproject.toml`
- Create: `.claudebot/requirements.txt`

- [ ] **Step 1: Create project files**

```python
# .claudebot/__init__.py
"""ClaudeDevBot Plugin - Injectable AI Development Assistant"""

__version__ = "0.1.0"
```

```toml
# .claudebot/pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "claudebot"
version = "0.1.0"
description = "Injectable AI Development Assistant Plugin"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0",
    "aiosqlite>=0.19.0",
]

[project.scripts]
claudebot = "claudebot.cli:main"
```

```txt
# .claudebot/requirements.txt
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pyyaml>=6.0
aiosqlite>=0.19.0
python-telegram-bot>=20.0
slowapi>=0.1.9
```

- [ ] **Step 2: Commit**

```bash
git add .claudebot/__init__.py .claudebot/pyproject.toml .claudebot/requirements.txt
git commit -m "feat: create plugin project structure"
```

---

### Task 2: Create Package Modules

**Files:**
- Create: `.claudebot/api/__init__.py`
- Create: `.claudebot/api/server.py`
- Create: `.claudebot/api/routes/__init__.py`
- Create: `.claudebot/api/routes/tasks.py`
- Create: `.claudebot/api/routes/health.py`

- [ ] **Step 1: Create api/__init__.py**

```python
# .claudebot/api/__init__.py
"""REST API for ClaudeDevBot Plugin"""

from .server import app

__all__ = ["app"]
```

- [ ] **Step 2: Create server.py**

```python
# .claudebot/api/server.py
"""FastAPI server for ClaudeDevBot Plugin"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import tasks, health

app = FastAPI(
    title="ClaudeDevBot Plugin API",
    description="REST API for AI-driven development workflows",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
```

- [ ] **Step 3: Create routes/__init__.py**

```python
# .claudebot/api/routes/__init__.py
"""API routes"""

from . import tasks, health

__all__ = ["tasks", "health"]
```

- [ ] **Step 4: Create health.py**

```python
# .claudebot/api/routes/health.py
"""Health check endpoints"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    version: str

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="0.1.0")
```

- [ ] **Step 5: Create tasks.py (stub)**

```python
# .claudebot/api/routes/tasks.py
"""Task endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter()

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
    CANCELLED = "cancelled"

class CreateTaskRequest(BaseModel):
    type: TaskType
    description: str
    files: List[str] = []
    branch: str = "main"
    priority: int = 0

class CreateTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime

class TaskDetailResponse(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# In-memory storage (will be replaced with orchestrator)
tasks_db: dict[str, TaskDetailResponse] = {}

@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest):
    task_id = str(uuid.uuid4())
    task = TaskDetailResponse(
        id=task_id,
        type=request.type,
        status=TaskStatus.PENDING,
        description=request.description,
        created_at=datetime.now()
    )
    tasks_db[task_id] = task
    return CreateTaskResponse(
        task_id=task_id,
        status=task.status,
        created_at=task.created_at
    )

@router.get("/tasks", response_model=List[TaskDetailResponse])
async def list_tasks():
    return list(tasks_db.values())

@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks_db[task_id]
    task.status = TaskStatus.CANCELLED
    return {"status": "cancelled"}
```

- [ ] **Step 6: Commit**

```bash
git add .claudebot/api/
git commit -m "feat: create API server structure with basic routes"
```

---

## Chunk 2: Data Models & Database

### Task 3: Create Database Models

**Files:**
- Create: `.claudebot/db/__init__.py`
- Create: `.claudebot/db/models.py`

- [ ] **Step 1: Create db/__init__.py**

```python
# .claudebot/db/__init__.py
"""Database models and utilities"""

from .models import Task, init_db, get_db

__all__ = ["Task", "init_db", "get_db"]
```

- [ ] **Step 2: Create models.py**

```python
# .claudebot/db/models.py
"""SQLite database models"""

import aiosqlite
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum

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
    CANCELLED = "cancelled"

class Task(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    repo_path: str
    branch: Optional[str] = None
    files: str = "[]"  # JSON array
    result: Optional[str] = None  # JSON object
    error: Optional[str] = None
    logs: str = "[]"  # JSON array
    priority: int = 0
    max_retries: int = 3
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

DB_PATH = ".claudebot/tasks.db"

async def init_db():
    """Initialize database schema"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                branch TEXT,
                files TEXT DEFAULT '[]',
                result TEXT,
                error TEXT,
                logs TEXT DEFAULT '[]',
                priority INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)
        """)
        await db.commit()

async def get_db():
    """Get database connection"""
    return aiosqlite.connect(DB_PATH)
```

- [ ] **Step 3: Commit**

```bash
git add .claudebot/db/
git commit -m "feat: add SQLite database models"
```

---

## Chunk 3: Agent Base Class & Tools

### Task 4: Create Agent Base Class

**Files:**
- Create: `.claudebot/agents/__init__.py`
- Create: `.claudebot/agents/base_agent.py`

- [ ] **Step 1: Create agents/__init__.py**

```python
# .claudebot/agents/__init__.py
"""Agent implementations"""

from .base_agent import BaseAgent, AgentContext, AgentResult
from .code_agent import CodeAgent
from .spec_agent import SpecAgent

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "CodeAgent",
    "SpecAgent",
]
```

- [ ] **Step 2: Create base_agent.py**

```python
# .claudebot/agents/base_agent.py
"""Base agent class and interfaces"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentContext:
    """Context passed to all agents"""
    repo_path: str
    branch: str
    claude_api_key: str
    config: dict

@dataclass
class AgentResult:
    """Standard result from any agent"""
    success: bool
    summary: str
    files_created: List[str] = []
    files_modified: List[str] = []
    logs: List[str] = []
    error: Optional[str] = None

class BaseAgent(ABC):
    """Abstract base class for all agents"""

    name: str = "base"
    description: str = "Base agent"

    @abstractmethod
    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute the agent task. Returns result with files and logs."""
        pass

    @abstractmethod
    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input. Returns (is_valid, error_message)"""
        pass

    def get_required_files(self, task: dict) -> List[str]:
        """Return list of files agent needs to read"""
        return []

    async def on_error(self, error: Exception, task: dict) -> AgentResult:
        """Handle errors - can be overridden for custom recovery"""
        logger.exception(f"Agent {self.name} error: {error}")
        return AgentResult(
            success=False,
            summary=f"Error: {str(error)}",
            error=str(error)
        )
```

- [ ] **Step 3: Commit**

```bash
git add .claudebot/agents/base_agent.py
git commit -m "feat: add base agent class and interfaces"
```

---

### Task 5: Create Tools

**Files:**
- Create: `.claudebot/tools/__init__.py`
- Create: `.claudebot/tools/claude_cli.py`

- [ ] **Step 1: Create tools/__init__.py**

```python
# .claudebot/tools/__init__.py
"""Tools for agents"""

from .claude_cli import ClaudeCLI

__all__ = ["ClaudeCLI"]
```

- [ ] **Step 2: Create claude_cli.py**

```python
# .claudebot/tools/claude_cli.py
"""Claude CLI wrapper"""

import subprocess
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ClaudeCLI:
    """Wrapper for Claude Code CLI"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.env = os.environ.copy()
        self.env["ANTHROPIC_API_KEY"] = api_key

    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a prompt to Claude and get completion"""
        cmd = ["claude", "--print", prompt]

        if system_prompt:
            cmd.insert(2, "--system")
            cmd.insert(3, system_prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=300
            )

            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise TimeoutError("Claude CLI timed out")
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code.")

    async def complete_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """Send a prompt to Claude and parse JSON response"""
        full_prompt = f"{prompt}\n\nRespond with valid JSON only."
        result = await self.complete(full_prompt, system_prompt)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add .claudebot/tools/
git commit -m "feat: add Claude CLI wrapper tool"
```

---

## Chunk 4: Code Agent Implementation

### Task 6: Implement Code Agent

**Files:**
- Create: `.claudebot/agents/code_agent.py`

- [ ] **Step 1: Create code_agent.py**

```python
# .claudebot/agents/code_agent.py
"""Code generation agent"""

import os
import logging
from typing import Optional

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)

class CodeAgent(BaseAgent):
    """Agent for generating code from descriptions"""

    name = "code"
    description = "Generate code from descriptions"

    SYSTEM_PROMPT = """You are an expert software developer. Generate code based on the user's description.

Rules:
1. Only output the code, no explanations
2. Use appropriate language/framework based on existing files
3. Follow best practices and coding standards
4. If multiple files are needed, separate them with ---FILE:filename---"""

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute code generation"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")
        files = task.get("files", [])

        # Read existing files for context
        file_contents = {}
        for file_path in files:
            full_path = os.path.join(context.repo_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    file_contents[file_path] = f.read()

        # Build context prompt
        context_prompt = f"Generate code for: {description}\n\n"
        if file_contents:
            context_prompt += "Existing files:\n"
            for path, content in file_contents.items():
                context_prompt += f"\n---{path}---\n{content}\n"

        # Call Claude
        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(context_prompt, self.SYSTEM_PROMPT)

            # Parse and write files
            modified_files = []
            current_file = None
            current_content = []

            for line in result.split('\n'):
                if line.startswith('---FILE:'):
                    if current_file and current_content:
                        file_path = os.path.join(context.repo_path, current_file)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w') as f:
                            f.write('\n'.join(current_content))
                        modified_files.append(current_file)
                    current_file = line.replace('---FILE:', '').replace('---', '').strip()
                    current_content = []
                elif current_file:
                    current_content.append(line)
                else:
                    # Single file output (backwards compatible)
                    if not current_file and file_contents:
                        # Modify first existing file
                        current_file = files[0] if files else "output.py"
                        current_content = [line]

            # Write last file
            if current_file and current_content:
                file_path = os.path.join(context.repo_path, current_file)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write('\n'.join(current_content))
                if current_file not in modified_files:
                    modified_files.append(current_file)

            return AgentResult(
                success=True,
                summary=f"Generated {len(modified_files)} file(s)",
                files_modified=modified_files
            )

        except Exception as e:
            logger.exception("Code generation failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description"):
            return False, "Description is required"
        return True, None
```

- [ ] **Step 2: Commit**

```bash
git add .claudebot/agents/code_agent.py
git commit -m "feat: implement Code Agent"
```

---

## Chunk 5: CLI & Server Integration

### Task 7: Create CLI

**Files:**
- Create: `.claudebot/cli.py`

- [ ] **Step 1: Create cli.py**

```python
# .claudebot/cli.py
"""CLI entry point for ClaudeDevBot Plugin"""

import sys
import os
import asyncio
import logging

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.server import app
from db.models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="ClaudeDevBot Plugin CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="localhost", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a task directly")
    run_parser.add_argument("type", choices=["spec", "code", "test", "deploy", "debug"], help="Task type")
    run_parser.add_argument("description", help="Task description")

    args = parser.parse_args()

    if args.command == "serve":
        asyncio.run(serve(args))
    elif args.command == "run":
        asyncio.run(run_task(args))
    else:
        parser.print_help()

async def serve(args):
    """Start the API server"""
    import uvicorn

    # Initialize database
    await init_db()

    # Validate config
    if not os.environ.get("CLAUDE_API_KEY"):
        logger.warning("CLAUDE_API_KEY not set. Set with: export CLAUDE_API_KEY=your-api-key")

    logger.info(f"Starting server on {args.host}:{args.port}")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )

async def run_task(args):
    """Run a task directly"""
    from agents.code_agent import CodeAgent
    from agents.base_agent import AgentContext
    from db.models import init_db

    await init_db()

    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        logger.error("CLAUDE_API_KEY not set")
        sys.exit(1)

    task = {
        "type": args.type,
        "description": args.description,
        "files": []
    }

    context = AgentContext(
        repo_path=os.getcwd(),
        branch="main",
        claude_api_key=api_key,
        config={}
    )

    agent = CodeAgent()
    result = await agent.execute(task, context)

    if result.success:
        print(f"✓ {result.summary}")
        print(f"Files: {result.files_modified}")
    else:
        print(f"✗ {result.error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add .claudebot/cli.py
git commit -m "feat: add CLI entry point"
```

---

## Chunk 6: Config & Init

### Task 8: Create Config & Init

**Files:**
- Create: `.claudebot/config.yaml`
- Create: `.claudebot/cli_commands.py` (for init command)

- [ ] **Step 1: Create config.yaml**

```yaml
# .claudebot/config.yaml
server:
  host: "localhost"
  port: 8765
  port_auto_increment: true

agents:
  enabled:
    - spec
    - code
    - test
    - deploy
    - debug
  timeout: 300

claude:
  model: "claude-3-5-sonnet-20241022"

git:
  auto_commit: false
  default_branch: "main"
```

- [ ] **Step 2: Add init command to cli.py**

```python
# Add to cli.py - import section
import yaml
from pathlib import Path

# Add after run_task function
async def init_project():
    """Initialize .claudebot in current directory"""
    claudebot_dir = Path(".claudebot")

    if claudebot_dir.exists():
        logger.warning(".claudebot/ already exists")
        return

    claudebot_dir.mkdir()

    # Copy template files
    template_dir = Path(__file__).parent

    files_to_copy = [
        "__init__.py",
        "config.yaml",
        "requirements.txt",
        "pyproject.toml",
    ]

    for file in files_to_copy:
        src = template_dir / file
        if src.exists():
            dst = claudebot_dir / file
            # For config, copy as-is
            if file == "config.yaml":
                import shutil
                shutil.copy(src, dst)
            else:
                import shutil
                shutil.copy(src, dst)

    logger.info("Initialized .claudebot/ in current directory")
    logger.info("Run: claudebot serve")

# Update main() to add init command
# In the subparsers section, add:
init_parser = subparsers.add_parser("init", help="Initialize .claudebot in current directory")

# Update the command handler:
if args.command == "init":
    asyncio.run(init_project())
elif args.command == "serve":
```

- [ ] **Step 3: Commit**

```bash
git add .claudebot/config.yaml .claudebot/cli.py
git commit -m "feat: add config and init command"
```

---

## Chunk 7: Orchestrator

### Task 9: Create Orchestrator

**Files:**
- Create: `.claudebot/orchestrator/__init__.py`
- Create: `.claudebot/orchestrator/task_manager.py`

- [ ] **Step 1: Create orchestrator/__init__.py**

```python
# .claudebot/orchestrator/__init__.py
"""Task orchestration"""

from .task_manager import TaskManager

__all__ = ["TaskManager"]
```

- [ ] **Step 2: Create task_manager.py**

```python
# .claudebot/orchestrator/task_manager.py
"""Task manager with queue and agent execution"""

import asyncio
import os
import logging
from datetime import datetime
from typing import Optional
import uuid

from ..agents.base_agent import AgentContext
from ..agents.code_agent import CodeAgent
from ..agents.spec_agent import SpecAgent
from ..db.models import Task, TaskType, TaskStatus, init_db, get_db

logger = logging.getLogger(__name__)

class TaskManager:
    """Manages task queue and agent execution"""

    def __init__(self, config: dict):
        self.config = config
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.cancelled_tasks: set[str] = set()

    async def start(self):
        """Start the task manager"""
        await init_db()
        asyncio.create_task(self._process_queue())

    async def create_task(self, task_data: dict) -> Task:
        """Create and queue a new task"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        task = Task(
            id=task_id,
            type=TaskType(task_data["type"]),
            status=TaskStatus.PENDING,
            description=task_data["description"],
            repo_path=task_data.get("repo_path", os.getcwd()),
            branch=task_data.get("branch", "main"),
            files=str(task_data.get("files", [])),
            priority=task_data.get("priority", 0),
            created_at=now
        )

        # Save to database
        async with await get_db() as db:
            await db.execute("""
                INSERT INTO tasks (id, type, status, description, repo_path, branch, files, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task.id, task.type.value, task.status.value, task.description,
                  task.repo_path, task.branch, task.files, task.priority, task.created_at))
            await db.commit()

        await self.queue.put(task)
        return task

    async def _process_queue(self):
        """Main loop - processes queued tasks"""
        while True:
            task = await self.queue.get()
            await self._execute_task(task)
            self.queue.task_done()

    async def _execute_task(self, task: Task):
        """Execute a single task with the appropriate agent"""
        # Check if cancelled
        if task.id in self.cancelled_tasks:
            await self._update_status(task.id, TaskStatus.CANCELLED)
            return

        await self._update_status(task.id, TaskStatus.RUNNING, started_at=datetime.now().isoformat())
        self.running_tasks[task.id] = asyncio.current_task()

        try:
            # Get agent
            agent = self._get_agent(task.type)

            # Create context
            context = AgentContext(
                repo_path=task.repo_path,
                branch=task.branch,
                claude_api_key=os.environ["CLAUDE_API_KEY"],
                config=self.config
            )

            # Execute
            task_dict = {
                "description": task.description,
                "files": eval(task.files) if task.files else []
            }

            result = await agent.execute(task_dict, context)

            # Check cancellation again
            if task.id in self.cancelled_tasks:
                await self._update_status(task.id, TaskStatus.CANCELLED)
            else:
                await self._update_status(
                    task.id,
                    TaskStatus.COMPLETED,
                    completed_at=datetime.now().isoformat(),
                    result=str(result.__dict__)
                )

        except Exception as e:
            logger.exception(f"Task {task.id} failed")
            await self._update_status(
                task.id,
                TaskStatus.FAILED,
                completed_at=datetime.now().isoformat(),
                error=str(e)
            )

        finally:
            self.running_tasks.pop(task.id, None)

    def _get_agent(self, task_type: TaskType):
        """Get agent instance for task type"""
        agent_map = {
            TaskType.CODE: CodeAgent(),
            TaskType.SPEC: SpecAgent(),
            # Add other agents as implemented
        }

        if task_type not in agent_map:
            raise ValueError(f"Unknown task type: {task_type}")

        return agent_map[task_type]

    async def _update_status(self, task_id: str, status: TaskStatus, **kwargs):
        """Update task status in database"""
        async with await get_db() as db:
            set_clauses = ["status = ?"]
            values = [status.value]

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(task_id)

            await db.execute(
                f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            await db.commit()

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        self.cancelled_tasks.add(task_id)

        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            return True
        return False
```

- [ ] **Step 3: Commit**

```bash
git add .claudebot/orchestrator/
git commit -m "feat: add task orchestrator"
```

---

## Chunk 8: Remaining Agents

### Task 10: Implement Spec Agent

**Files:**
- Create: `.claudebot/agents/spec_agent.py`

- [ ] **Step 1: Create spec_agent.py**

```python
# .claudebot/agents/spec_agent.py
"""Spec generation agent"""

import os
import logging
from typing import Optional

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)

class SpecAgent(BaseAgent):
    """Agent for generating specifications"""

    name = "spec"
    description = "Generate specification documents"

    SYSTEM_PROMPT = """You are an expert technical writer. Create clear, detailed specifications.

Format: Markdown
Sections:
1. Overview
2. Requirements
3. Technical Design
4. API Specification (if applicable)
5. Acceptance Criteria"""

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute spec generation"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")

        # Check for existing SPEC.md
        spec_path = os.path.join(context.repo_path, "SPEC.md")
        existing_spec = ""
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                existing_spec = f.read()

        prompt = f"Generate specification for: {description}\n\n"
        if existing_spec:
            prompt += f"Existing spec:\n{existing_spec}\n"

        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(prompt, self.SYSTEM_PROMPT)

            # Write SPEC.md
            with open(spec_path, 'w') as f:
                f.write(result)

            return AgentResult(
                success=True,
                summary="Generated SPEC.md",
                files_created=["SPEC.md"]
            )

        except Exception as e:
            logger.exception("Spec generation failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description"):
            return False, "Description is required"
        return True, None
```

- [ ] **Step 2: Commit**

```bash
git add .claudebot/agents/spec_agent.py
git commit -m "feat: implement Spec Agent"
```

---

## Chunk 9: API Integration with Orchestrator

### Task 11: Update API to Use Orchestrator

**Files:**
- Modify: `.claudebot/api/routes/tasks.py`

- [ ] **Step 1: Update tasks.py to use TaskManager**

```python
# .claudebot/api/routes/tasks.py - Updated
"""Task endpoints with orchestrator"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

router = APIRouter()

# Global task manager (will be initialized by server)
_task_manager = None

def set_task_manager(manager):
    """Set the global task manager"""
    global _task_manager
    _task_manager = manager

class CreateTaskRequest(BaseModel):
    type: str
    description: str
    files: List[str] = []
    branch: str = "main"
    priority: int = 0
    repo_path: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    description: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[str] = None

@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    if _task_manager is None:
        raise HTTPException(status_code=500, detail="Task manager not initialized")

    task_data = {
        "type": request.type,
        "description": request.description,
        "files": request.files,
        "branch": request.branch,
        "priority": request.priority,
        "repo_path": request.repo_path or ""
    }

    task = await _task_manager.create_task(task_data)

    return TaskResponse(
        id=task.id,
        type=task.type.value,
        status=task.status.value,
        description=task.description,
        created_at=task.created_at
    )

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    if _task_manager is None:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    # TODO: Implement list from database
    return []

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    if _task_manager is None:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    # TODO: Implement get from database
    raise HTTPException(status_code=404, detail="Task not found")

@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    if _task_manager is None:
        raise HTTPException(status_code=500, detail="Task manager not initialized")

    success = await _task_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"status": "cancelled"}
```

- [ ] **Step 2: Update server.py to initialize TaskManager**

```python
# .claudebot/api/server.py - Updated
"""FastAPI server for ClaudeDevBot Plugin"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yaml

from .routes import tasks, health
from ..orchestrator.task_manager import TaskManager

app = FastAPI(
    title="ClaudeDevBot Plugin API",
    description="REST API for AI-driven development workflows",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize task manager
_config = {}
try:
    with open(".claudebot/config.yaml") as f:
        _config = yaml.safe_load(f)
except FileNotFoundError:
    pass

_task_manager = TaskManager(_config.get("agents", {}))

# Set task manager in routes
tasks.set_task_manager(_task_manager)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])

@app.on_event("startup")
async def startup():
    await _task_manager.start()
```

- [ ] **Step 3: Commit**

```bash
git add .claudebot/api/server.py .claudebot/api/routes/tasks.py
git commit -m "feat: integrate orchestrator with API"
```

---

## Chunk 10: Telegram Integration

### Task 12: Create Telegram Integration

**Files:**
- Create: `.claudebot/telegram_bot.py`

- [ ] **Step 1: Create telegram_bot.py**

```python
# .claudebot/telegram_bot.py
"""Telegram bot integration"""

import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Telegram bot will be implemented as a separate module
# that calls the plugin API

class TelegramBot:
    """Telegram bot that communicates with plugin API"""

    def __init__(self, api_url: str = "http://localhost:8765"):
        self.api_url = api_url
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set")

    async def send_message(self, chat_id: str, text: str):
        """Send message to Telegram user"""
        # Will use python-telegram-bot
        pass

    async def send_task_result(self, chat_id: str, task_id: str):
        """Send task result to user"""
        # Call API to get task result
        pass

    async def start_polling(self):
        """Start polling for task completion"""
        # Poll API for running tasks
        # Send updates when complete
        pass
```

- [ ] **Step 2: Commit**

```bash
git add .claudebot/telegram_bot.py
git commit -m "feat: add Telegram bot stub"
```

---

## Summary

This plan covers:
- Project structure setup
- Database models
- Agent base class and tools
- Code and Spec agents
- CLI with serve/run commands
- Config and init
- Task orchestrator
- API integration
- Telegram integration stub

Total: ~10 major tasks with detailed steps

---

**Plan complete and saved to `docs/superpowers/plans/2026-03-17-claudebot-plugin-plan.md`. Ready to execute?**

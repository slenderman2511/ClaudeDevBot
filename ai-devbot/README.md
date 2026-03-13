# AI DevBot

An autonomous multi-agent AI system for executing development tasks through Telegram commands.

## Overview

AI DevBot allows developers to send commands from Telegram and have AI agents execute engineering workflows including:

- **Specification Generation** (`/spec`)
- **Code Generation** (`/code`)
- **Test Execution** (`/test`)
- **Service Deployment** (`/deploy`)
- **Debugging Assistance** (`/debug`)
- **Status Check** (`/status`)

## Architecture

The system follows a modular multi-agent architecture:

```
┌─────────────────────────────────────────────────┐
│           Telegram Interface (bot/)              │
├─────────────────────────────────────────────────┤
│        Workflow Orchestration (workflows/)        │
├──────────┬──────────┬──────────┬──────────┬──────┤
│ Spec     │ Code     │ Test     │ Deploy   │Debug │
│ Agent    │ Agent    │ Agent    │ Agent    │Agent │
├──────────┴──────────┴──────────┴──────────┴──────┤
│              Tools (tools/)                       │
│  Claude CLI │ Telegram API │ Git Tools            │
├─────────────┴─────────────┴──────────────────────┤
│   Guardrails    │   Observability   │   Tests    │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
ai-devbot/
├── config/           # Configuration files
│   ├── config.yaml   # Main configuration
│   └── __init__.py  # Config loader
├── spec/             # Specification documents
│   ├── product.md    # Product specification
│   ├── architecture.md # Architecture design
│   └── api.yaml     # API specification
├── data/             # Data and memory
│   └── memory/
│       ├── short_term/  # Ephemeral memory
│       └── long_term/  # Persistent memory
├── agents/           # AI agents
│   ├── base_agent.py   # Base agent class
│   ├── spec_agent.py   # Specification agent
│   ├── code_agent.py   # Code generation agent
│   ├── test_agent.py   # Test execution agent
│   ├── deploy_agent.py # Deployment agent
│   └── debug_agent.py  # Debugging agent
├── tools/            # Tool interfaces
│   ├── tool.py         # Base tool class
│   ├── claude_cli.py  # Claude CLI wrapper
│   ├── telegram_api.py # Telegram API
│   └── git_tools.py   # Git operations
├── workflows/         # Workflow orchestration
│   ├── command_router.py  # Command parsing
│   ├── orchestration.py   # Agent coordination
│   └── task_planner.py   # Execution planning
├── observability/     # Monitoring & logging
│   ├── logging.py     # Structured logging
│   ├── tracing.py     # Distributed tracing
│   └── metrics.py     # Metrics collection
├── guardrails/        # Security & validation
│   ├── permissions.py     # Access control
│   └── command_validation.py # Input validation
├── bot/              # Telegram bot
│   └── telegram_bot.py    # Main bot entry
├── tests/            # Test suite
│   ├── test_agents.py
│   └── test_workflows.py
└── README.md
```

## Installation

```bash
# Clone the repository
cd ai-devbot

# Install dependencies (when implemented)
# pip install -r requirements.txt
```

## Configuration

Configure the bot by editing `config/config.yaml`:

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"

claude:
  model: "sonnet"

agents:
  spec_agent:
    model: "sonnet"
    max_iterations: 10
```

Set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
```

## Usage

1. Start the bot:
   ```bash
   python -m bot.telegram_bot
   ```

2. Send commands to your Telegram bot:
   - `/spec Create a user authentication system`
   - `/code Implement login endpoint`
   - `/test Run all tests`
   - `/deploy staging`
   - `/debug Connection timeout error`
   - `/status`

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`:
   ```python
   from agents.base_agent import BaseAgent, Task, AgentResult

   class MyAgent(BaseAgent):
       def execute(self, task: Task) -> AgentResult:
           # Implement agent logic
           return AgentResult(success=True, output="...")
   ```

2. Register the agent in the orchestrator.

## Architecture Layers

1. **Configuration Layer** - YAML-based config with env var substitution
2. **Data/Memory Layer** - Short-term and long-term memory
3. **Agent Layer** - BaseAgent + specialized agents
4. **Tools Layer** - Tool abstraction for LLM integration
5. **Workflow Orchestration** - Command routing and task planning
6. **Observability** - Logging, tracing, metrics
7. **Guardrails** - Permissions and validation
8. **Tests** - Unit and integration tests

## License

MIT

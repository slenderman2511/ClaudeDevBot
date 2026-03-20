# ClaudeDevBot

> Unified AI development assistant — CLI tooling, FastAPI plugin system, and Telegram bot, all in one.

## Install

Install directly from GitHub:

```bash
pip install git+https://github.com/claudebot/claudebot.git
```

Or clone and install locally:

```bash
git clone https://github.com/claudebot/claudebot.git
cd claudebot
pip install src/
```

For development (editable install — changes reflect immediately):

```bash
pip install -e src/
```

## Setup

1. **Get a Claude API key** from [console.anthropic.com](https://console.anthropic.com)

2. **Set the environment variable:**
   ```bash
   export CLAUDE_API_KEY="your-key-here"
   ```

3. **Initialize in your project:**
   ```bash
   claudebot init
   ```

## CLI Commands

```bash
claudebot init                     # Full setup: scan + graph (interactive)
claudebot --path <dir> init        # Init a specific directory

claudebot scan                     # Detect tech stack → .devbot/project_profile.json
claudebot graph                    # Build code graph → .devbot/code_graph.json

claudebot feature <name>           # Create OpenSpec feature
claudebot feature <name> -d "desc" # Create with description
claudebot plan <name>              # Generate task plan from feature
claudebot implement <name>         # Implement feature via AI agents

claudebot config --list            # Show all config
claudebot config --get key         # Get specific key
claudebot config --set key value   # Set a value
claudebot status                   # Show DevBot status
claudebot list                     # List available features

claudebot serve --port 8765        # Start FastAPI server
claudebot serve --telegram         # Start API + Telegram bot
claudebot run code "task desc"     # Run a task directly (spec|code|test|deploy|debug)
```

## Features

| Feature | Description |
|---------|-------------|
| **5 AI Agents** | Spec, Code, Test, Deploy, Debug |
| **REST API** | Programmatic access to all agents |
| **WebSocket** | Real-time task updates |
| **Telegram Bot** | Control via Telegram long polling |
| **Project Scanner** | Auto-detect tech stack |
| **Code Graph** | Knowledge graph of your codebase |
| **OpenSpec** | Structured feature management |
| **SQLite DB** | Persistent task history |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/tasks` | Create a new task |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{id}` | Get task by ID |
| `DELETE` | `/api/tasks/{id}` | Cancel a task |
| `WS` | `/ws/tasks` | WebSocket for real-time updates |

## Configuration

### `config.yaml`
```yaml
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

claude:
  model: "claude-3-5-sonnet-20241022"
  api_key: ""   # Leave empty; use CLAUDE_API_KEY env var instead

telegram:
  enabled: false
  bot_token: ""  # Set TELEGRAM_BOT_TOKEN env var
```

### `.claudebotrc` (quick overrides)
```ini
port = 8766
host = 0.0.0.0
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_API_KEY` | Yes | Claude API key for AI agents |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token (for Telegram integration) |
| `CLAUDEBOT_PORT` | No | Override default server port |
| `CLAUDEBOT_API_KEY` | No | API key for REST endpoint authentication |

## Architecture

```
claudebot/
├── src/                          # src-layout root
│   ├── pyproject.toml            # Package root (install from here)
│   └── claudebot/               # The package
│       ├── cli.py                # CLI entry point
│       ├── cli_commands/         # CLI command implementations
│       ├── agents/               # AI agents (spec, code, test, deploy, debug)
│       ├── api/                  # FastAPI server + routes
│       │   └── routes/           # REST + WebSocket endpoints
│       ├── scanner/              # Project analysis
│       ├── graph/                # Code knowledge graph
│       ├── spec/                 # OpenSpec feature management
│       ├── db/                   # SQLite task database
│       ├── memory/               # Short & long term memory
│       ├── tools/                # Tool wrappers (Claude CLI, Git)
│       └── observability/        # Structured logging + tracing
└── openspec/                    # Feature specs (created by init)
    ├── features/
    └── plans/
```

## Requirements

- Python 3.10+
- [Claude API key](https://console.anthropic.com)

## License

MIT

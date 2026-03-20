# ClaudeDevBot Plugin

Injectable AI Development Assistant Plugin - brings AI-powered development workflows to any repository.

## Features

- **5 AI Agents**: Spec, Code, Test, Deploy, Debug
- **REST API**: Programmatic access to all agents
- **CLI**: Direct command-line interface
- **WebSocket**: Real-time task updates
- **Telegram Integration**: Control via Telegram bot
- **Plugin Architecture**: Installable via pip

## Quick Start

```bash
# Install
pip install claudebot

# Initialize in your project
claudebot init

# Start API server
claudebot serve

# Run a task directly
claudebot run code "Add user authentication"
```

## Configuration

### config.yaml
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
```

### .claudebotrc (Quick overrides)
```ini
port = 8766
host = 0.0.0.0
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLAUDE_API_KEY` | Claude API key (required) |
| `CLAUDEBOT_API_KEY` | API key for REST access |
| `CLAUDEBOT_PORT` | Override default port |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create task |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Get task status |
| DELETE | `/api/tasks/{id}` | Cancel task |
| GET | `/api/health` | Health check |
| WS | `/ws/tasks` | WebSocket for real-time updates |

## License

MIT

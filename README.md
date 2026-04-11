# Agent World

A real-time 3D multi-agent visualization platform. Watch AI agents work in a cyberpunk-themed world.

![screenshot](screenshot.png)

## Features

- **Real-time 3D Visualization**: Agents rendered as glowing orbs in a 3D world
- **Room-based Organization**: Agents work in different rooms (Forge, Library, Market)
- **Live Activity Monitoring**: See what each agent is doing in real-time
- **Task Management**: Assign tasks and watch progress
- **WebSocket Communication**: Instant updates across all connected clients

## Quick Start

### 1. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs on http://localhost:8000

### 2. Start the Frontend

The frontend is pure HTML/JS - just open it:

```bash
cd frontend
# Option 1: Simple Python server
python -m http.server 8080

# Option 2: VS Code Live Server extension
# Right-click index.html → Open with Live Server
```

Open http://localhost:8080 in your browser.

## Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   Frontend  │ ◄────────────────► │   Backend   │
│  (Three.js) │                    │  (FastAPI)  │
└─────────────┘                    └──────┬──────┘
                                          │
                                    ┌─────┴─────┐
                                    │  In-Mem   │
                                    │  Storage  │
                                    └───────────┘
```

## Project Structure

```
agent-world/
├── backend/
│   ├── main.py              # FastAPI app with WebSocket
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── index.html           # UI layout (cyberpunk theme)
    └── game.js              # Three.js 3D world
```

## API Endpoints

- `GET /api/agents` - List all agents
- `GET /api/agents/{id}` - Get agent details
- `POST /api/agents/{id}/move` - Move agent to room
- `POST /api/agents/{id}/task` - Assign task
- `POST /api/agents/{id}/pause` - Pause agent
- `WS /ws/world` - WebSocket for real-time updates

## WebSocket Events

**Client → Server:**
- `spawn_agent` - Create new agent
- `assign_task` - Give agent work
- `move_agent` - Move to different room

**Server → Client:**
- `world_init` - Initial world state
- `agent_moved` - Agent changed rooms
- `agent_progress` - Task progress update
- `task_completed` - Task finished
- `agent_spawned` - New agent created

## Customization

### Add More Rooms

Edit `init_world()` in `backend/main.py`:

```python
rooms["my-room"] = Room(
    id="my-room",
    name="My Room",
    x=10,
    y=10,
    color="#ff6b35",
    agents=[]
)
```

### Change Agent Colors

Edit agent colors in `backend/main.py`:

```python
agent_colors = ["#00f3ff", "#ff006e", "#39ff14", "#ffb347"]
```

### Use Real LLM

Replace the simulation in `simulate_task()` with actual API calls:

```python
import anthropic

client = anthropic.Anthropic(api_key="your-key")

async def execute_task(agent, task):
    response = await client.messages.create(
        model="claude-3-sonnet-20240229",
        messages=[{"role": "user", "content": task.description}]
    )
    return response.content
```

## Next Steps

- [ ] Add PostgreSQL for persistence
- [ ] Add authentication
- [ ] Implement real LLM integration
- [ ] Add more 3D assets
- [ ] Create room customization UI

## License

MIT

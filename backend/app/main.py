import json
import logging
from pathlib import Path
from typing import Dict, List, Set

from app.detection.base import DraftEvent
from app.draft import DraftManager
from app.models import DraftState, Hero
from app.scoring import score_heroes
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hots-draft")

app = FastAPI(title="Heroes of the Storm Draft Helper API")

# Serve static files from the data directory
repo_root = Path(__file__).resolve().parents[2]
app.mount("/data", StaticFiles(directory=str(repo_root / "data")), name="data")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared memory state
HERO_DB: Dict[str, Hero] = {}
DRAFT_MANAGER = DraftManager(my_team_first=True)
ACTIVE_WEBSOCKETS: Set[WebSocket] = set()


def load_hero_db():
    global HERO_DB
    repo_root = Path(__file__).resolve().parents[2]
    heroes_json_path = repo_root / "data" / "heroes.json"

    if not heroes_json_path.exists():
        logger.error(f"Database not found at {heroes_json_path}")
        HERO_DB = {}
        return

    try:
        with open(heroes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        adapter = TypeAdapter(List[Hero])
        heroes = adapter.validate_python(data)
        HERO_DB = {hero.id: hero for hero in heroes}
        logger.info(f"Loaded {len(HERO_DB)} heroes successfully.")
    except Exception as e:
        logger.error(f"Failed to load heroes database: {e}")


@app.on_event("startup")
async def startup_event():
    load_hero_db()


def get_current_payload() -> dict:
    """Helper to compile current draft state and recommendations."""
    recs = score_heroes(
        DraftState(
            map_name=DRAFT_MANAGER.map_name,
            my_team_picks=DRAFT_MANAGER.my_team_picks,
            my_team_bans=DRAFT_MANAGER.my_team_bans,
            enemy_picks=DRAFT_MANAGER.enemy_picks,
            enemy_bans=DRAFT_MANAGER.enemy_bans,
        ),
        HERO_DB,
    )

    # Format the current step
    current_step = DRAFT_MANAGER.get_current_step()
    step_data = None
    if current_step:
        step_data = {
            "action": current_step.action,
            "team": current_step.team,
            "index": DRAFT_MANAGER.current_step_idx,
        }

    return {
        "draft_state": {
            "map_name": DRAFT_MANAGER.map_name,
            "my_team_picks": DRAFT_MANAGER.my_team_picks,
            "my_team_bans": DRAFT_MANAGER.my_team_bans,
            "enemy_picks": DRAFT_MANAGER.enemy_picks,
            "enemy_bans": DRAFT_MANAGER.enemy_bans,
            "my_team_first": DRAFT_MANAGER.my_team_first,
            "is_complete": DRAFT_MANAGER.is_complete(),
            "current_step": step_data,
        },
        "recommendations": [rec.model_dump() for rec in recs],
    }


async def broadcast_state():
    """Broadcast the updated draft state and recommendations to all clients."""
    if not ACTIVE_WEBSOCKETS:
        return

    payload = get_current_payload()
    dead_sockets = set()

    for ws in ACTIVE_WEBSOCKETS:
        try:
            await ws.send_json(payload)
        except Exception:
            dead_sockets.add(ws)

    for ws in dead_sockets:
        ACTIVE_WEBSOCKETS.remove(ws)


@app.get("/api/heroes", response_model=List[Hero])
async def get_heroes():
    return list(HERO_DB.values())


@app.post("/api/db/reload")
async def reload_db():
    load_hero_db()
    await broadcast_state()
    return {"status": "ok", "message": f"Reloaded {len(HERO_DB)} heroes"}


@app.get("/api/draft/state")
async def get_draft_state():
    return get_current_payload()


@app.post("/api/draft/event")
async def post_draft_event(event: DraftEvent):
    global DRAFT_MANAGER

    logger.info(
        f"Received draft event: {event.event_type} - {event.hero_id or event.map_name}"
    )

    if event.event_type == "set_first_pick":
        if event.my_team_first is None:
            raise HTTPException(
                status_code=400, detail="my_team_first is required for set_first_pick"
            )
        # Save map name when resetting
        old_map = DRAFT_MANAGER.map_name
        DRAFT_MANAGER = DraftManager(
            my_team_first=event.my_team_first, map_name=old_map
        )

    elif event.event_type == "map_select":
        DRAFT_MANAGER.map_name = event.map_name

    elif event.event_type == "reset":
        DRAFT_MANAGER.reset()

    elif event.event_type == "undo":
        DRAFT_MANAGER.undo_last_action()

    elif event.event_type in ("pick", "ban"):
        if not event.hero_id:
            raise HTTPException(
                status_code=400, detail="hero_id is required for pick/ban events"
            )
        if event.hero_id not in HERO_DB:
            raise HTTPException(
                status_code=400, detail=f"Unknown hero_id: {event.hero_id}"
            )

        success = DRAFT_MANAGER.apply_action(event.hero_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Draft is already complete or invalid state transition",
            )

    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported event_type: {event.event_type}"
        )

    # Broadcast changes to all open connections
    await broadcast_state()
    return {"status": "ok"}


@app.websocket("/ws/draft")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ACTIVE_WEBSOCKETS.add(websocket)
    logger.info("WebSocket connection established.")

    # Send initial state immediately
    try:
        await websocket.send_json(get_current_payload())
        while True:
            # Keep connection alive; events flow from HTTP endpoint,
            # but we listen in case client sends messages
            data = await websocket.receive_text()
            # If the client wants to send events via WebSocket
            try:
                event_data = json.loads(data)
                event = DraftEvent.model_validate(event_data)
                # Re-route to same logic as HTTP post
                await post_draft_event(event)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_json({"error": str(e)})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    finally:
        ACTIVE_WEBSOCKETS.discard(websocket)

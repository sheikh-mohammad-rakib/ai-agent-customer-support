import json
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.request_validator import RequestValidator

from config import (
    PORT, HOST,
    DASHSCOPE_API_KEY, ASR_MODEL, LLM_MODEL, TTS_MODEL,
    TWILIO_AUTH_TOKEN, ADMIN_TOKEN
)
from database import (
    get_all_orders,
    get_all_faqs,
    get_recent_transcripts,
    get_recent_tool_logs,
    get_connection,
    seed_data
)
from voice_agent import QwenVoiceSession

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Acme Retail — Qwen Cloud Voice AI Customer Support",
    description="Real-time Telephony & Browser Voice AI Customer Support Agent powered by Qwen Cloud",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active websocket simulator sessions for broadcasting UI updates
active_ui_sessions = set()


@app.get("/api/config", response_class=JSONResponse)
async def get_config_info():
    """Returns current active Qwen Cloud model configuration and connection status."""
    has_key = bool(DASHSCOPE_API_KEY and len(DASHSCOPE_API_KEY) > 10)
    return {
        "status": "ready" if has_key else "missing_key",
        "asr_model": ASR_MODEL,
        "llm_model": LLM_MODEL,
        "tts_model": TTS_MODEL,
        "api_provider": "Alibaba Cloud / Qwen Cloud (DashScope)"
    }


@app.get("/api/orders", response_class=JSONResponse)
async def list_orders():
    """List all orders in the customer database."""
    return {"orders": get_all_orders()}


@app.get("/api/faqs", response_class=JSONResponse)
async def list_faqs():
    """List all policy FAQs in the knowledge base."""
    return {"faqs": get_all_faqs()}


@app.get("/api/transcripts", response_class=JSONResponse)
async def list_transcripts(limit: int = 50):
    """List recent call transcripts."""
    return {"transcripts": get_recent_transcripts(limit)}


@app.get("/api/tool-logs", response_class=JSONResponse)
async def list_tool_logs(limit: int = 20):
    """List recent automated tool executions."""
    return {"tool_logs": get_recent_tool_logs(limit)}


@app.post("/api/reset-db")
async def reset_database(request: Request):
    """Reset and re-seed the PostgreSQL sample database. Requires X-Admin-Token header."""
    token = request.headers.get("X-Admin-Token", "")
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Unauthorized: invalid or missing X-Admin-Token header."})
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM faqs")
    cur.execute("DELETE FROM calls")
    cur.execute("DELETE FROM call_transcripts")
    cur.execute("DELETE FROM tool_logs")
    conn.commit()
    seed_data(conn)
    cur.close()
    conn.close()
    return {"success": True, "message": "Demo database re-seeded with sample orders and FAQs."}


@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    """
    Twilio webhook returning TwiML response to open a bidirectional WebSocket Media Stream.
    Validates Twilio request signature when TWILIO_AUTH_TOKEN is configured.
    """
    # Validate Twilio signature if auth token is configured
    if TWILIO_AUTH_TOKEN:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        form_data = await request.form()
        params = dict(form_data)
        url = str(request.url)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(url, params, signature):
            logger.warning("Invalid Twilio signature on /incoming-call — rejecting request.")
            return Response(content="Forbidden", status_code=403)

    host = request.headers.get("host", f"localhost:{PORT}")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting you to Nova, Acme Retail Customer Support.</Say>
    <Connect>
        <Stream url="wss://{host}/media-stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def twilio_media_stream_ws(websocket: WebSocket):
    """
    Twilio Voice Media Stream bi-directional WebSocket handler.
    """
    await websocket.accept()
    logger.info("Twilio media stream WebSocket connected")
    session = QwenVoiceSession(websocket, call_id="TWILIO_CALL", caller_number="PSTN Caller")

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            event = data.get("event")
            if event == "connected":
                logger.info("Twilio stream connected event received")
            elif event == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"]["callSid"]
                session.call_id = call_sid
                logger.info(f"Twilio stream started: {stream_sid} (Call: {call_sid})")
                await session.speak_and_reply(
                    "Hello! Thank you for calling Acme Retail customer support. My name is Nova. How can I help you today?"
                )
            elif event == "stop":
                logger.info("Twilio media stream stopped")
                break
    except WebSocketDisconnect:
        logger.info("Twilio websocket disconnected")
    finally:
        await session.close()


@app.websocket("/browser-stream")
async def browser_simulator_ws(websocket: WebSocket):
    """
    Browser Voice Simulator WebSocket bridge.
    Allows real-time voice & text interactive testing from the web dashboard.
    """
    await websocket.accept()
    active_ui_sessions.add(websocket)
    logger.info("Browser Simulator WebSocket connected")

    session = QwenVoiceSession(websocket, call_id="BROWSER_SIM", caller_number="Web Simulator")

    # Welcome greeting on connection
    await session.send_event("status", {"state": "connected", "label": "Connected to Qwen Cloud Agent"})
    await session.speak_and_reply(
        "Hi there! I'm Nova, your Acme Retail AI support specialist powered by Qwen Cloud. Ask me about an order like ORD-1001, return policies, or initiating an RMA return!"
    )

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                msg_type = data.get("type")

                if msg_type == "user_message":
                    user_text = data.get("text", "")
                    await session.handle_user_message(user_text)

                elif msg_type == "ping":
                    await session.send_event("pong", {})

                elif msg_type == "trigger_greeting":
                    await session.speak_and_reply(
                        "Hello! How can I assist you with your Acme Retail order today?"
                    )
            except json.JSONDecodeError:
                # Handle raw text if not JSON
                await session.handle_user_message(msg)

    except WebSocketDisconnect:
        logger.info("Browser simulator websocket disconnected")
    finally:
        active_ui_sessions.discard(websocket)
        await session.close()


# Mount static web dashboard UI
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

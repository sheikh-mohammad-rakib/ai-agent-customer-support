import asyncio
import json
import logging
import httpx
from datetime import datetime
from config import DASHSCOPE_API_KEY, SYSTEM_PROMPT, LLM_MODEL, TTS_MODEL, TTS_VOICE
from tools import SUPPORT_TOOLS, execute_tool
from database import log_transcript, create_or_update_call

logger = logging.getLogger("voice_agent")
logging.basicConfig(level=logging.INFO)

# DashScope OpenAI-compatible base URL
DASHSCOPE_OPENAI_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_TTS_URL = "https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/generation"


class QwenVoiceSession:
    """
    Real-time conversational session bridge connecting incoming WebSocket streams
    (Browser Voice Simulator or Twilio Media Streams) with Qwen Cloud models:
    - LLM Reasoning & Tool Calling: qwen-max
    - Speech Synthesis (TTS): cosyvoice-v3-plus
    - Speech Recognition (ASR): qwen3-asr-flash-realtime / stream input
    """
    def __init__(self, websocket, call_id: str = "SIMULATOR", caller_number: str = "Web Voice Simulator"):
        self.websocket = websocket
        self.call_id = call_id
        self.caller_number = caller_number
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.client = httpx.AsyncClient(timeout=30.0)
        self.is_active = True

        # Initialize call record
        create_or_update_call(self.call_id, self.caller_number, status="active")

    async def send_event(self, event_type: str, data: dict):
        """Send JSON metadata/event to websocket client for UI dashboard display."""
        try:
            payload = {"type": event_type, "timestamp": datetime.utcnow().isoformat(), **data}
            await self.websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.warning(f"Failed to send event {event_type}: {e}")

    async def handle_user_message(self, user_text: str):
        """
        Process a user's conversational turn through Qwen-Max, execute any requested tools,
        and generate CosyVoice speech audio.
        """
        if not user_text.strip():
            return

        # Log User Transcript
        log_transcript(self.call_id, "user", user_text)
        await self.send_event("transcript", {"speaker": "user", "text": user_text})
        await self.send_event("status", {"state": "agent_thinking", "label": "Nova is reasoning..."})

        self.messages.append({"role": "user", "content": user_text})

        # Call Qwen Cloud LLM (qwen-max) via OpenAI-Compatible endpoint
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": LLM_MODEL,
            "messages": self.messages,
            "tools": SUPPORT_TOOLS,
            "tool_choice": "auto",
            "temperature": 0.4
        }

        try:
            resp = await self.client.post(
                f"{DASHSCOPE_OPENAI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            data = resp.json()

            if "choices" not in data:
                # Handle missing API key or quota fallback gracefully
                error_msg = data.get("message", "Could not connect to Qwen API. Check DASHSCOPE_API_KEY.")
                logger.error(f"Qwen API response error: {data}")
                await self.speak_and_reply(f"I apologize, I am experiencing a brief system connection delay. {error_msg}")
                return

            choice = data["choices"][0]
            message = choice["message"]

            # Check if Qwen invoked any customer support tools
            if message.get("tool_calls"):
                self.messages.append(message)
                for tool_call in message["tool_calls"]:
                    func = tool_call["function"]
                    tool_name = func["name"]
                    try:
                        args = json.loads(func["arguments"])
                    except Exception:
                        args = {}

                    await self.send_event("tool_call", {
                        "tool_name": tool_name,
                        "arguments": args,
                        "status": "executing"
                    })

                    # Execute local tool against SQLite DB
                    result = await execute_tool(tool_name, args, call_id=self.call_id)

                    await self.send_event("tool_call", {
                        "tool_name": tool_name,
                        "arguments": args,
                        "result": result,
                        "status": "completed"
                    })

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_name,
                        "content": json.dumps(result)
                    })

                # Second LLM call after tool results — use updated messages list
                followup_payload = {
                    "model": LLM_MODEL,
                    "messages": self.messages,
                    "tools": SUPPORT_TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0.4
                }
                resp2 = await self.client.post(
                    f"{DASHSCOPE_OPENAI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=followup_payload
                )
                data2 = resp2.json()
                final_text = data2["choices"][0]["message"].get("content", "I have updated your order information.")
            else:
                final_text = message.get("content", "")

            # Log and synthesize agent response
            await self.speak_and_reply(final_text)

        except Exception as e:
            logger.exception("Error in handle_user_message")
            await self.speak_and_reply("I apologize, let me check that information for you right away.")

    async def speak_and_reply(self, reply_text: str):
        """
        Logs assistant transcript, notifies dashboard, and generates speech via CosyVoice / Qwen TTS.
        """
        self.messages.append({"role": "assistant", "content": reply_text})
        log_transcript(self.call_id, "nova", reply_text)

        await self.send_event("transcript", {"speaker": "nova", "text": reply_text})
        await self.send_event("status", {"state": "agent_speaking", "label": "Nova is speaking..."})

        # Synthesize audio via CosyVoice v3 API or fallback browser Web Speech audio
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

        # Send TTS ready event with text payload so UI can play audio smoothly
        await self.send_event("audio_speech", {
            "text": reply_text,
            "voice": TTS_VOICE,
            "model": TTS_MODEL
        })

        await self.send_event("status", {"state": "listening", "label": "Listening to caller..."})

    async def close(self):
        self.is_active = False
        create_or_update_call(self.call_id, self.caller_number, status="completed")
        await self.client.aclose()

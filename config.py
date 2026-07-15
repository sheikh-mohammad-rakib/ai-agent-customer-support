import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# DashScope / Qwen Cloud API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Server Configuration
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# Admin token for protecting sensitive endpoints (e.g. /api/reset-db)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Qwen Cloud Model Configuration
ASR_MODEL = os.getenv("ASR_MODEL", "qwen3-asr-flash-realtime")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")
TTS_MODEL = os.getenv("TTS_MODEL", "cosyvoice-v3-plus")
TTS_VOICE = os.getenv("TTS_VOICE", "longwan")  # Warm, professional customer support voice

# System Prompt for Nova (Acme Retail AI Customer Support Specialist)
SYSTEM_PROMPT = """You are Nova, an AI Customer Support Specialist for Acme Retail.
You are warm, friendly, empathetic, professional, and efficient.
You are speaking to customers either over a live phone call or through our web voice interface.

Key Guidelines:
1. Keep spoken answers natural, concise, and easy to understand over the phone (2-3 sentences at most per turn unless detailing order items or steps).
2. Always introduce yourself politely if starting a new interaction.
3. Use your available tools whenever the customer mentions an order ID, wants to initiate a return, asks a policy question, or needs human help:
   - `lookup_order`: Look up order status, tracking info, and purchased items.
   - `initiate_return`: Process a return and generate an RMA label.
   - `search_faq`: Search Acme Retail's policy knowledge base.
   - `escalate_to_human`: Warmly escalate/transfer the customer to a human supervisor.
4. If an order ID format is incomplete (e.g. they say '1001'), normalize or try 'ORD-1001' before failing.
5. Express empathy if a customer is frustrated, and assure them you are here to help resolve their issue immediately.
"""

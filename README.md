# Acme Retail — Qwen Cloud Voice AI Customer Support Agent

A production-grade, real-time Telephony & Browser Voice AI Customer Support Agent powered natively by **Qwen Cloud (`qwen3-asr-flash-realtime` + `qwen-max` + `cosyvoice-v3-plus`)**.

## Features

1. **Qwen Cloud 3-Model Pipeline**:
   - **Speech-to-Text (`qwen3-asr-flash-realtime`)**: Low-latency streaming speech recognition.
   - **Reasoning & Tool Execution (`qwen-max`)**: Conversational e-commerce support specialist persona (**Nova**) with automated function calling (`lookup_order`, `initiate_return`, `search_faq`, `escalate_to_human`).
   - **Natural Voice Synthesis (`cosyvoice-v3-plus`)**: Ultra-realistic voice generation for human-like responses.
2. **Supervisor Web Dashboard & Browser Simulator**:
   - Real-time speaker turns and audio frequency visualizer.
   - Live inspection of tool call executions and SQLite database (`support_agent.db`).
   - Quick one-click test chips to simulate common e-commerce support workflows.
3. **Twilio Telephony Ready**:
   - Includes webhook endpoint (`POST /incoming-call`) and bidirectional WebSocket Media Stream bridge (`/media-stream`) to handle live PSTN phone calls.

---

## Getting Started

### 1. Environment Configuration
Your API key is already configured in `.env`:
```env
DASHSCOPE_API_KEY=your_qwen_cloud_api_key_here
PORT=8000
```

### 2. Install Dependencies
Open your terminal and install Python dependencies:
```powershell
pip install -r requirements.txt
```

### 3. Run the Server
Start the FastAPI server:
```powershell
uvicorn main:app --reload --port 8000
```

### 4. Open the Web Dashboard & Simulator
Open your browser and navigate to:
```
http://localhost:8000
```
- Click **"Connect Simulator"** to connect to the Qwen Cloud voice agent.
- Click **"Voice Speak"** to talk through your microphone, or type your message / click a quick prompt chip!

---

## Sample Test Orders in SQLite Database
- **`ORD-1001`**: Alex Mercer ($199.99) — *Delivered* (FedEx)
- **`ORD-1002`**: Samantha Chen ($274.50) — *In Transit* (UPS)
- **`ORD-1003`**: Marcus Vance ($129.00) — *Pending Return* (USPS)

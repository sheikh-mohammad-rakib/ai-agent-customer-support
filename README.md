# Acme Retail — Qwen Cloud Voice AI Customer Support Agent

A production-grade, real-time Telephony & Browser Voice AI Customer Support Agent powered natively by **Qwen Cloud (`qwen3-asr-flash-realtime` + `qwen-max` + `cosyvoice-v3-plus`)**, deployed on **Render** with a managed **PostgreSQL** database.

## Features

1. **Qwen Cloud 3-Model Pipeline**:
   - **Speech-to-Text (`qwen3-asr-flash-realtime`)**: Low-latency streaming speech recognition.
   - **Reasoning & Tool Execution (`qwen-max`)**: Conversational e-commerce support specialist persona (**Nova**) with automated function calling (`lookup_order`, `initiate_return`, `search_faq`, `escalate_to_human`).
   - **Natural Voice Synthesis (`cosyvoice-v3-plus`)**: Ultra-realistic voice generation for human-like responses.
2. **Supervisor Web Dashboard & Browser Simulator**:
   - Real-time speaker turns and audio frequency visualizer.
   - Live inspection of tool call executions and PostgreSQL database.
   - Quick one-click test chips to simulate common e-commerce support workflows.
3. **Twilio Telephony**:
   - Webhook endpoint (`POST /incoming-call`) with **Twilio signature validation** and bidirectional WebSocket Media Stream bridge (`/media-stream`) for live PSTN phone calls.
4. **Render Deployment Ready**:
   - `render.yaml` Blueprint declares both the web service and linked PostgreSQL database in one file.
   - Python 3.12 pinned via `runtime.txt`.

---

## Getting Started (Local Development)

### 1. Clone & Create Environment File

```powershell
cp .env.example .env
```

Fill in your values in `.env`:

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DATABASE_URL=postgresql://user:password@host:5432/dbname
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
ADMIN_TOKEN=any_secret_string_you_choose
PORT=8000
```

> For local development you can use a free [Neon](https://neon.tech) or [Supabase](https://supabase.com) PostgreSQL instance for `DATABASE_URL`.

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run the Server

```powershell
uvicorn main:app --reload --port 8000
```

### 4. Open the Web Dashboard & Simulator

Navigate to `http://localhost:8000`

- Click **"Connect Simulator"** to connect to the Qwen Cloud voice agent.
- Click **"Voice Speak"** to talk through your microphone, or type a message / click a quick prompt chip!

---

## Deploying to Render

### 1. Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### 2. Deploy via Render Blueprint

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect your GitHub account and select the repo
3. Render reads `render.yaml` and automatically creates:
   - The **web service** (Python, uvicorn)
   - A linked **PostgreSQL database** (`acme-support-db`)

### 3. Set Secret Environment Variables

In the Render dashboard → your web service → **Environment**, add:

| Variable | Value |
|---|---|
| `DASHSCOPE_API_KEY` | Your Qwen Cloud / DashScope key |
| `TWILIO_ACCOUNT_SID` | From your [Twilio console](https://console.twilio.com) |
| `TWILIO_AUTH_TOKEN` | From your [Twilio console](https://console.twilio.com) |
| `ADMIN_TOKEN` | Any secret string you choose |

> `DATABASE_URL` is injected **automatically** by Render — do not set it manually.

### 4. Wire Your Twilio Phone Number

In the Twilio console, set the webhook for your phone number:
- **When a call comes in** → `POST` → `https://<your-service>.onrender.com/incoming-call`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web dashboard & browser simulator |
| `GET` | `/api/config` | Active model config & API key status |
| `GET` | `/api/orders` | List all orders in the database |
| `GET` | `/api/faqs` | List all policy FAQs |
| `GET` | `/api/transcripts` | Recent call transcripts |
| `GET` | `/api/tool-logs` | Recent tool execution logs |
| `POST` | `/api/reset-db` | Re-seed database *(requires `X-Admin-Token` header)* |
| `POST` | `/incoming-call` | Twilio webhook — returns TwiML *(signature validated)* |
| `WS` | `/media-stream` | Twilio bidirectional audio stream |
| `WS` | `/browser-stream` | Browser simulator voice stream |

---

## Sample Test Orders

| Order ID | Customer | Total | Status | Carrier |
|---|---|---|---|---|
| `ORD-1001` | Alex Mercer | $199.99 | Delivered | FedEx |
| `ORD-1002` | Samantha Chen | $274.50 | In Transit | UPS |
| `ORD-1003` | Marcus Vance | $129.00 | Pending Return | USPS |

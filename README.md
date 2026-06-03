# LinkedIn Engagement Assistant

An AI-assisted LinkedIn engagement platform that helps professionals draft thoughtful replies, generate high-performing posts, discover trending discussions, and organize engagement workflows.

> **This is an augmentation tool, not a bot.** Every LinkedIn action requires explicit user confirmation. The system never auto-posts, auto-likes, auto-connects, auto-messages, or simulates human activity.

---

## Architecture Overview

```
linkedin-engagement-assistant/
├── extension/          # Chrome Extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js   # Service worker: message routing, API abstraction
│   ├── content/        # LinkedIn DOM integration
│   ├── popup/          # Quick-action popup
│   ├── sidebar/        # Persistent AI sidebar dashboard
│   ├── styles/         # LinkedIn-native UI styles
│   └── utils/          # Shared utilities (API, storage, sanitization)
│
├── backend/            # FastAPI AI + orchestration layer
│   ├── app/
│   │   ├── api/        # Route handlers
│   │   ├── services/   # Business logic
│   │   ├── llm/        # LLM provider adapters (OpenAI, Gemini, Anthropic)
│   │   ├── scraping/   # Trend discovery scrapers
│   │   ├── models/     # ORM + Pydantic schemas
│   │   ├── middleware/  # Auth, logging, rate limiting
│   │   ├── prompts/    # Centralized prompt templates
│   │   ├── config/     # Settings management
│   │   └── utils/      # Caching, text utilities
│   ├── tests/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── shared/
│   ├── api-contracts/  # OpenAPI specification
│   └── schemas/        # Shared TypeScript type definitions
│
└── docker-compose.yml
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+ (optional, for TypeScript types)
- Chrome/Chromium browser
- Docker + Docker Compose (optional)

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

Start the backend server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Chrome Extension Setup

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` directory
5. The extension icon will appear in your toolbar

### 3. Docker (Full Stack)

```bash
docker-compose up --build
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | Yes (if using OpenAI) |
| `GEMINI_API_KEY` | Google Gemini API key | Yes (if using Gemini) |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `LLM_PROVIDER` | `openai` / `gemini` / `anthropic` | Yes |
| `API_SECRET_KEY` | Extension ↔ backend auth key | Yes |
| `ALLOWED_ORIGINS` | CORS whitelist | Yes |
| `DATABASE_URL` | SQLite or PostgreSQL URL | Yes |
| `REDIS_URL` | Redis for caching (optional) | No |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` | No |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/draft-reply` | Generate AI reply drafts |
| `POST` | `/api/generate-post` | Generate LinkedIn post variations |
| `GET` | `/api/trends` | Fetch trending topics |
| `POST` | `/api/analyze-post` | Analyze post quality |
| `GET` | `/api/health` | Health check |

Full OpenAPI spec: `shared/api-contracts/openapi.yaml`

---

## Example API Requests

### Draft Reply

```bash
curl -X POST http://localhost:8000/api/draft-reply \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "author_name": "Jane Smith",
    "author_role": "CTO at TechCorp",
    "post_content": "AI will replace most software engineers by 2027.",
    "tone": "contrarian",
    "persona": "senior_engineer"
  }'
```

### Generate Post

```bash
curl -X POST http://localhost:8000/api/generate-post \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "topic": "Lessons from shipping to 1M users",
    "style": "founder",
    "include_cta": true,
    "variations": 3
  }'
```

---

## Safety & Compliance

This tool strictly follows LinkedIn's User Agreement:

- **No automated posting** — all drafts require manual copy-paste or user click
- **No automated engagement** — no auto-like, auto-comment, auto-connect
- **No mass messaging** — no bulk message tools
- **No CAPTCHA bypass** — no evasion mechanisms
- **No scraped private data** — only public post content visible to the logged-in user

The extension reads page content to provide context for AI generation. It does not submit any forms, click any buttons, or perform any actions without explicit user confirmation.

---

## Supported Tones & Personas

### Tones
- `professional` — Formal, authoritative
- `concise` — Short, punchy
- `expert` — Technical depth
- `contrarian` — Respectfully challenges assumptions
- `founder` — Vision-driven, story-first
- `recruiter` — People-focused, warm

### Personas
- `senior_engineer` — Technical credibility
- `product_manager` — User-centric insights
- `executive` — Strategic perspective
- `entrepreneur` — Growth mindset
- `researcher` — Evidence-based
- `consultant` — Framework-driven

---

## Testing

```bash
cd backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html
```

---

## Production Deployment

### Render / Railway / Fly.io

1. Set environment variables in the platform dashboard
2. Point the `DATABASE_URL` to a hosted PostgreSQL instance
3. Deploy the `backend/` directory
4. Update `extension/utils/api.js` `DEFAULT_BACKEND_URL` to your production URL
5. Package the extension (`zip -r extension.zip extension/`)

### VPS (with Docker)

```bash
# On your server
git clone <repo>
cd my-linkedin-assistant
cp backend/.env.example backend/.env
# Edit backend/.env
docker-compose -f docker-compose.yml up -d
```

---

## Future Enhancements

- [x] LinkedIn Analytics dashboard — repurposed as extension usage dashboard (replies, posts, tokens, sessions)
- [x] Scheduled content calendar
- [x] A/B testing for post variations
- [ ] Team collaboration workspace
- [x] Browser fingerprint isolation for privacy (privacy mode toggle suppresses X-Extension-Version header)
- [x] Webhook notifications for reply opportunities
- [x] Fine-tuned personal writing style model
- [x] Export engagement history to CSV/PDF
- [x] Chrome Side Panel full integration (Side Panel API, keyboard shortcut Ctrl+Shift+L)
- [x] Firefox extension port (manifest.firefox.json, browser shim, build.ps1)

---

## Security Notes

- API keys are stored in `chrome.storage.local` (not exposed to content scripts)
- All backend communication uses `X-API-Key` header authentication
- Injected HTML is sanitized via `DOMPurify` patterns before insertion
- Content scripts have no access to extension storage keys
- `eval()` is never used
- CSP headers enforced on backend responses

---

## License

MIT — See LICENSE file.

# KYC Agent — AI-Powered Document Verification for Deriv

An intelligent KYC onboarding platform that uses Gemini Vision AI to analyze identity documents, detect quality issues, cross-validate form data, and route submissions through a risk-based compliance workflow.

Built for the **Deriv AI Talent Sprint 2026**.

## Quick Start

```bash
cd kyc-agent
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

# Add your Gemini API key
cp .env.example .env
# Edit .env: GEMINI_API_KEY=your_key_here

# Run
streamlit run frontend/kyc_onboarding.py
```

App opens at **http://localhost:8501**

## Features

**Client KYC Portal** — Guided multi-step onboarding wizard
- Country selection (Pakistan, UAE, UK)
- Dynamic form with real-time validation (CNIC, Emirates ID, Passport)
- Document upload with AI quality analysis (blur, glare, lighting, corners)
- OCR extraction + cross-validation against form data
- Side-aware document intelligence (CNIC back = address, Emirates ID back = DOB/gender)
- Utility bill age validation (max 3 months)
- Rental/moved address awareness

**Compliance Dashboard** — Internal admin tool
- Submissions queue with status filtering
- Manual review panel (side-by-side form vs OCR comparison)
- Risk alerts sorted by severity
- Analytics with approval rates, country breakdown, risk distribution

**AI Risk Scoring** — Hybrid rule-based + Gemini-powered engine
- 0-100 risk score with explainable factors
- Auto-routing: LOW = auto-approve, MEDIUM = review queue, HIGH = flagged
- Fraud indicators: manipulation detection, transliteration awareness, cross-field consistency

## Admin Dashboard Access

Sidebar > **Admin Access** > Password: `deriv2026`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| AI/OCR | Google Gemini 2.5 Flash |
| Backend | FastAPI (REST API) |
| Deriv API | WebSocket (wss://ws.derivws.com/websockets/v3) |
| Validation | Pydantic |
| Config | python-dotenv |

## Project Structure

```
kyc-agent/
├── frontend/
│   ├── kyc_onboarding.py        # Main app (client portal + dashboard nav)
│   ├── compliance_dashboard.py  # Internal compliance dashboard
│   ├── dynamic_form.py          # Country-specific form renderer
│   └── form_fields.py           # Reusable form components
├── backend/
│   ├── vision_analyzer.py       # Gemini Vision document analysis
│   ├── ocr_service.py           # OCR extraction + comparison
│   ├── issue_detector.py        # Quality issue detection (20+ types)
│   ├── risk_scorer.py           # Hybrid AI + rule-based risk engine
│   ├── llm_reasoner.py          # User-friendly guidance generation
│   ├── deriv_api.py             # Deriv WebSocket client + mock fallback
│   └── api.py                   # FastAPI REST endpoints
├── config/
│   ├── kyc_schemas.json         # Country-specific KYC requirements
│   ├── country_forms.json       # Dynamic form field schemas
│   └── settings.py              # Environment config (Pydantic)
└── .streamlit/
    └── config.toml              # Streamlit theme (Deriv dark mode)
```

## Supported Countries & Documents

| Country | Identity Documents | Address Proof |
|---------|-------------------|---------------|
| Pakistan | CNIC (front + back) | Utility Bill |
| UAE | Emirates ID (front + back) | Utility Bill |
| United Kingdom | Passport / Driving License | Utility Bill |

## Environment Variables

```env
GEMINI_API_KEY=your_key        # Required — Google Gemini API
DERIV_API_TOKEN=               # Optional — real Deriv API (leave blank for demo mode)
DERIV_APP_ID=1089              # Public demo app ID
DEMO_MODE=True                 # Mock Deriv responses (no account needed)
```

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Select repo, branch `main`, main file `frontend/kyc_onboarding.py`
4. Add `GEMINI_API_KEY` in Advanced Settings > Secrets
5. Deploy

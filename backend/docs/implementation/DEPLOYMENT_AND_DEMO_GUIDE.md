# ArogyaScribe Production Deployment & Live Demo Guide

## 1. Quick Start (Local Demo Mode)
The entire stack is configured with zero external friction. Local SQLite and mock AI engines are pre-configured to work immediately without setting up external cloud accounts.

### Backend Setup:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python scripts/seed_demo.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend Setup:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open [http://localhost:5173](http://localhost:5173) in Chrome.

---

## 2. Authentication & Demo Role Access
On `/login` or the Landing Page sign-in modal, operational clinic demo buttons allow 1-click test fill:
1. **Organization Admin (Clinic Owner):** `orgadmin@arogyacare.in` / `OrgAdmin@123`
2. **Receptionist (Front Desk):** `reception@arogyacare.in` / `Reception@123`
3. **Doctor (Clinical Workspace):** `dr.sharma@arogyacare.in` / `Doctor@123`

*Platform Owner (Super Admin)*: For production security, the Super Admin does not appear on public client-side quick-fill buttons. Authenticate with `superadmin@arogyascribe.in` and the secret password configured in `SUPERADMIN_INITIAL_PASSWORD` in `backend/.env`.

Once signed in to a clinic workspace, presenters can also switch roles on the fly using the **Quick Role Switch** buttons in the sidebar footer without logging out.

---

## 2.1 B2B Customer Onboarding Flow
1. Clinic submits registration request on Landing Page (`/` -> "Request Onboarding / Register").
2. Notification is dispatched to `OWNER_NOTIFICATION_EMAIL` and logged to `./storage/email_outbox.log`.
3. Platform Owner visits `/platform/organizations`, inspects pending inquiries, enters custom pricing/coupon override, and clicks **Approve & Generate Password**.
4. Clinic Org Admin logs in, views quota meters on `/org/staff`, and provisions staff.

---

## 3. Pan-India Multilingual Capabilities
ArogyaScribe natively supports **9 Indian Languages**:
- **English (`en`)**
- **Hindi (`hi` - हिन्दी)**
- **Tamil (`ta` - தமிழ்)**
- **Telugu (`te` - తెలుగు)**
- **Kannada (`kn` - ಕನ್ನಡ)**
- **Malayalam (`ml` - മലയാളം)**
- **Marathi (`mr` - मराठी)**
- **Bengali (`bn` - বাংলা)**
- **Gujarati (`gu` - ગુજરાતી)**

In the Doctor Workspace (Stage 4), doctors can download standard ReportLab PDFs or click **Print Indic Summary (Unicode)** to print vernacular summaries rendered with Google Noto Indic fonts.

---

## 4. Gnani AI Credit Guardrail & SHA-256 Cache
To conserve the hackathon's 5,000 Gnani credits:
1. Every audio chunk and LLM prompt is hashed via SHA-256 and cached locally in `./storage/gnani_cache/<hash>.json`.
2. A strict circuit breaker (`gnani_max_live_calls: 6`) blocks excessive live credit deduction and gracefully falls back to native high-accuracy clinical simulation.
3. Live status can be inspected at `GET /api/v1/platform/ai-status`.

---

## 5. Docker Deployment
### Run Backend Container:
```bash
cd backend
docker build -t arogyascribe-backend .
docker run -p 8000:8000 -e DATABASE_URL=sqlite:///demo.db arogyascribe-backend
```

### Run Frontend Container:
```bash
cd frontend
docker build -t arogyascribe-frontend .
docker run -p 80:80 arogyascribe-frontend
```

---

## 6. Vercel & Cloud Frontend Deployment
- Set `VITE_API_BASE_URL` in your Vercel Environment Variables to your deployed FastAPI backend URL (e.g. `https://api.yourdomain.com`).
- `frontend/vercel.json` ensures client-side routing is handled without 404s.


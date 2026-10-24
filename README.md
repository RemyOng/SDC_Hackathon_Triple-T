
---

# Orbyte GreenReady

> From Bills to Better Business, For SME

---

## Team Information

| Field                  | Details                                     
| ---------------------- | ------------------------------------------- 
| **Team Name**          | Remy Ong Jing Yi                             
| **Team Domain**        | Domain 2         
| **SDG Track (1–17)**   | SDG 8 - Decent Work and Economic Growth
| **Team Leader**        | Remy Ong Jing Yi                            
| **University**         | Asia Pacific University of Technology & Innovation                       
| **Number of Members**  | 3                              

## Links

| Resource          | Link                                           
| ----------------- | ---------------------------------------------- 
| GitHub Repository | https://github.com/RemyOng/SDC_Hackathon_Triple-T
| Live Demo         | https://sdc-hackathon-triple-t.replit.app/  
| RunPod Endpoint   | https://api.runpod.ai/v2/wsx3goo6yh5l85/runsync
| Slide Deck        | https://1drv.ms/p/c/2d5ba555e1972cec/IQCTQ4LKsVlESq3HNyd0NCKVASk34drC675Fdgz-gLxRVCc?e=AyOHEz   
| Demo Video        | https://youtu.be/gF99pr5NSAU       

---

## Overview

### Problem

Malaysian micro and small businesses often receive a monthly TNB bill but do not have
the time or expertise to check every charge or decide which energy upgrade will pay
back first. Quotes arrive in different formats, while the evidence needed by green
financiers and qualified suppliers is expensive for SMEs to prepare. GreenReady
turns a bill into checked, comparable energy-upgrade options and, with the owner's
consent, a privacy-first connection to investors and suppliers.

### Solution

GreenReady is an Orbyte module that accepts a TNB bill as a WhatsApp message or an
uploaded photo, PDF, or screenshot. AI extracts the bill fields and charge lines,
then deterministic rules validate the tariff calculations, identify usage spikes,
and compare LED lighting, inverter air conditioning, and rooftop solar using the
same savings, payback, and CO2e formulas. The owner can review uncertain fields,
approve an anonymous listing, and approve each connection before contact details
are shared.

### Key Features

- **Bill intake and validation** — Extract bill data with confidence scores and run
  eight checks against the applicable TNB tariff, including a six-month usage trend
  and spike alert.
- **Fair upgrade comparison** — Compare LED, inverter air conditioning, and solar
  using consistent cost, annual saving, payback, and CO2e calculations.
- **Preparation Pack and Opportunity Board** — Create checked evidence for the SME,
  keep listings anonymous, and enable consent-based connections with investors and
  suppliers.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | React, TypeScript, Vite, Tailwind CSS |
| Backend       | Python, FastAPI, Pydantic, Uvicorn |
| Database      | Supabase (PostgreSQL), with a local marketplace store for the prototype |
| AI / Compute  | RunPod Serverless with a Qwen2-VL document-extraction worker |
| Document processing | PyMuPDF, Google Gmail API, WhatsApp/Whapi integration |
| Hosting / Dev | Replit |

---

## Project Structure

```
.
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── core/                # Deterministic energy and financial calculations
│   ├── db/                  # Supabase access and seed data
│   ├── gmail_reader/        # Gmail bill intake and persistence
│   ├── marketplace/         # SME, investor, and supplier board APIs
│   ├── schema/              # Pydantic request and extraction schemas
│   ├── services/            # Document, RunPod, and Whapi integrations
│   ├── workflow/            # LangGraph extraction and validation workflow
│   └── frontend/            # React/TypeScript web application
├── submission/              # Proof-of-use and submission documents
├── tests/
│   └── test_marketplace.py  # Marketplace and calculation tests
├── LICENSE
├── requirements.txt         # Python dependencies
└── README.md
```

### Architecture

```
SME ──► WhatsApp / Gmail / Web upload
       │
       ▼
Replit FastAPI app ──► PyMuPDF + RunPod VLM extraction
       │                         │
       │                         ▼
       ├──► Supabase       Deterministic tariff checks
       │                         │
       ▼                         ▼
SME dashboard ◄── Opportunity Board ◄── Owner-approved connections
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the deployed [GreenReady app](https://sdc-hackathon-triple-t.replit.app/), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab (🔒) and add the variables listed in `.env.example`:
   - `RUNPOD_API_KEY`
   - `RUNPOD_ENDPOINT_ID`
3. Click **Run** and start the app with `python src/main.py` from the repository root.

The Python application and frontend source are in `src/`. Keep `requirements.txt`,
`.env`, `credentials.json`, and `token.json` in the repository root. The app
loads those root-level files from the code location, so the launch directory
does not change where it looks for configuration or Gmail OAuth credentials.

### Option 2 — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/RemyOng/SDC_Hackathon_Triple-T.git
cd SDC_Hackathon_Triple-T

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables in the repository-root .env file
#    (copy the variables from your deployment secrets)

# 5. Run the app
python src/main.py
```

### Run Tests

```bash
PYTHONPATH=src python -m unittest discover tests
```

---

## How We Use Replit *(Required)*

Replit was used to develop, run, and host the GreenReady prototype. The deployed
FastAPI application serves the backend and the built web interface at the live
demo link above.

- **Development:** The team used a Replit workspace to develop and test the
  FastAPI backend, marketplace workflow, and React frontend.
- **Hosting:** The application is deployed through Replit at
  `https://sdc-hackathon-triple-t.replit.app/`.
- **Secrets:** Runtime credentials such as `RUNPOD_API_KEY`, Supabase credentials,
  and messaging credentials are supplied through environment secrets rather than
  committed to source control.

📄 Proof of use: [`submission/SDC2026_Triple T_Replit_POU.pdf`](submission/SDC2026_Triple T_Replit_POU.pdf)

## How We Use RunPod *(Required)*

- **Workload:** RunPod performs Qwen2-VL vision-language inference on TNB bills
  and supplier documents. The model returns structured extraction data for the
  fields needed by the tariff checks and upgrade calculations.
- **Integration:** The Replit FastAPI app converts PDFs into page images with
  PyMuPDF, sends them to the RunPod Serverless Endpoint, and validates the
  response with Pydantic.
- **Reliability:** The client supports synchronous responses and queued jobs,
  polls queued jobs until completion, and reports failed or timed-out inference
  explicitly.

Example request:

```bash
curl -X POST https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "Hello"}}'
```

📄 Proof of use: [`submission/SDC2026_Triple T_Runpod_POU.pdf`](submission/SDC2026_Triple T_Runpod_POU.pdf)

---

## Challenges & Learnings

- **Unreliable document formats:** TNB bills can arrive as PDFs, photos, or
  screenshots. The pipeline normalizes PDFs into page images, accepts common image
  formats, and keeps a manual-entry path for fields that need correction.
- **AI extraction must not determine financial outcomes:** The model only reads
  documents. Fixed tariff rules perform the arithmetic and bill checks, while
  confidence thresholds route uncertain fields to staff review.
- **Privacy and consent:** Investors and suppliers initially see anonymised
  listings. Contact details are unlocked only after the SME owner accepts a
  connection, and actions are recorded in the activity log.
- **Lesson learned:** A useful SME workflow needs both automation and transparent
  human approval; accurate extraction alone is not enough to make an upgrade
  decision trustworthy.

## Future Improvements

- [ ] Verify savings against each new bill after an upgrade and generate a
      monthly savings history.
- [ ] Add efficient motors, refrigeration, chillers, heat-pump water heaters, and
      air compressors to the comparison engine.
- [ ] Support email forwarding, myTNB and smart-meter exports, plus Sabah and
      Sarawak tariffs.
- [ ] Add supplier quote bidding, investor matching alerts, and portfolio views
      for kWh and CO2e saved.
- [ ] Add Bahasa Malaysia and Chinese summaries and alerts.

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Remy Ong Jing Yi | Team Lead / Backend / Frontend | [@RemyOng](https://github.com/RemyOng) |
| Saeed Omar Abdulrahman | Backend / Replit + Runpod         | [@Omar-Saeed-OASS](https://github.com/Omar-Saeed-OASS) |
| Chua Pei Ying | Frontend / Business        | [@Peiying](https://github.com/Pyyp0409) |

---

## Submission Checklist

- [✓] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [✓] Slide deck link added
- [✓] Demo video link added
- [✓] Replit used, with proof of use in `submission/`
- [✓] RunPod used, with proof of use in `submission/`
- [✓] Replit proof of use completed (`submission/SDC2026_Triple T_Replit_POU.pdf`)
- [✓] RunPod proof of use completed (`submission/SDC2026_Triple T_Runpod_POU.pdf`)
- [✓] "How to Run" steps verified
- [✓] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).

# SDC Hackathon Triple-T

This project ingests WhatsApp documents and upcoming Gmail messages in
parallel, stores both sources in Supabase, validates Gmail attachments/content
through LangGraph, and exposes the WhatsApp workflow through FastAPI.

## Setup

1. Create a Google Cloud OAuth desktop application with the Gmail API enabled.
2. Download its OAuth client file as `credentials.json` in the project root.
   This file is ignored by Git and must never be committed.
3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Run the combined WhatsApp and Gmail service:

   ```powershell
   python main.py
   ```

   The API is available at `http://localhost:8000`. The WhatsApp webhook
   remains at `/webhook/whapi`, while Gmail is polled every 10 seconds in a
   background task. Gmail attachments are uploaded to the `raw_documents`
   Supabase bucket and registered in `ingested_documents` with
   `source_channel = GMAIL`.

   To run only the Gmail reader instead, use `python run_gmail_reader.py`.
   Its API is available at `http://localhost:8000`; use `GET /emails`,
   `POST /check-now`, or `GET /docs`.

The first run opens a browser for Gmail authorization and stores the refresh
token in `token.json`. Set `GMAIL_QUERY` and `GMAIL_MAX_RESULTS` to customize
which messages are read.

## Opportunity Board (web app)

The board, partner requests, investor EOI and supplier proposal run without
Supabase, RunPod or Gmail credentials, on synthetic demo data (spec §7):

```powershell
cd frontend; npm install; npm run build; cd ..
python run_board.py            # http://localhost:8001/app
```

`python main.py` also serves the board API and the built app at `/app`.
For front-end development run `python run_board.py` and `npm run dev` in
`frontend/` (Vite proxies `/api` to port 8001).

Switch roles from the button in the top bar (Demo mode), or open a link
such as `/app/investor/board?role=investor`. Roles: `sme_owner`, `sme_staff`,
`investor` (Bank Hijau), `supplier` (Suria Hijau Solar), `ops` (Reset demo
under Audit log).

Demo path: Supplier → Send proposal on GR-L-0871 · Investor → Request to
connect · Owner → Requests → Accept both (staff are blocked, rule C05) ·
Investor → Connections → Send EOI · Owner → Accept EOI · Activity shows every step.

| Module | Purpose |
|---|---|
| `marketplace/rules.py` | Bands, upgrade estimates (reuses `core/calculator.py`), criteria match (M02), repayment check |
| `marketplace/views.py` | What each role may see; identity only after acceptance (M05) |
| `marketplace/documents.py` | EOI and proposal drafts from the Word templates in `source files/` |
| `marketplace/orbyte.py` | Mock Orbyte menus, action items and wallet in Orbyte's own API shapes |
| `marketplace/api.py` | REST endpoints under `/api/greenready` |
| `marketplace/store.py` | In-memory store standing in for the Supabase tables |

Run the tests with `python -m unittest tests.test_marketplace`.

## LangGraph boundary

`gmail_reader.read_gmail_messages()` is the direct async Gmail input function;
Gmail retrieval is not a LangGraph. After retrieval, the FastAPI poller invokes
`workflow.validation_subgraph.build_validation_subgraph()` asynchronously,
which runs:

1. Attachment corruption checks for empty files, extensions, signatures,
   archives, UTF-8 text, and Gmail base64 data.
2. Image/PDF-only format checking.
3. TNB-bill and spam/phishing heuristics using the email subject and body.

The poller records Gmail message IDs in `processed_email_ids.json`, primes
itself with existing messages on startup, and only processes messages that
arrive after the service starts. Each new message is persisted using the same
SME, storage, document, and audit-log tables as WhatsApp, keyed by the sender's
email address. Validated TNB attachments use the same RunPod extraction shape as
WhatsApp (`document_type`, `account_number`, `company_name`, `baseline_kwh`,
`target_capex_myr`, and `equipment_type`); spam messages are stored with
`document_type = SPAM`.

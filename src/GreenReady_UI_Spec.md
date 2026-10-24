# Orbyte GreenReady — UI & Deployment Specification

**Tagline:** From Bills to Better Business
**Team:** Triple T (APU) · XMUM SDC Hackathon 2026 · Domain 2 — Orbyte Smart SME Challenge
**Version:** Final business model (GreenReady = Orbyte's own module, usage-based pricing) · 24 Oct 2026

---

## 0. What this document is for

This is the build spec for the **live prototype** (submission item 3) and the **GitHub repo** (item 5). It lists every screen, component, state, field and rule the UI needs, plus the design tokens (colour palette and Inter typography) and the deployment checklist.

**Non-negotiables from the organisers**

| Requirement | What it means for the UI |
|---|---|
| Live prototype link, not a video or static mock-up | Every screen in the demo path must be clickable and backed by real (synthetic) data and real rule calculations |
| GitHub must reflect what you demo | No hard-coded screenshots; the demo runs from the repo |
| Domain 2 must-haves | Show the chain **trigger → connected data → decision logic → human approval → logged outcome** on screen |
| Human control | Every listing and every connection needs an explicit owner **Approve / Accept** click |
| Orbyte fit and reuse | The UI looks and behaves like a module **inside Orbyte** (Orbyte shell, Orbyte credit wallet, Orbyte approvals, audit log) |
| Ease of learning | One main action per screen; a first-time owner gets a result from one bill in under 3 minutes |
| AI policy | Every AI tool, model and dataset is declared; the UI labels AI-read fields with confidence scores |

**Rubric hooks (preliminary round)**

- **Innovation 30%** → the Upgrade Comparison screen (seller-free, same formulas) and the anonymous, consent-based Opportunity Board.
- **Problem–solution fit 25%** → the full journey visible in one demo pass, with the owner in control.
- **Feasibility 25%** → the most important feature (Fair Upgrade Comparison) works live; the hardest risk (AI misreads a bill) shows its fallback live (confidence gate → staff review → manual entry).
- **Clarity 20%** → plain labels, the same numbers as the deck and proposal.

---

## 1. Product context

### 1.1 Role

GreenReady is a **new module inside Orbyte** (Alpha Red Pro Sdn Bhd). Team Triple T designs it; Orbyte would own and run it. The UI must therefore sit **inside the Orbyte shell**, not look like a separate app.

### 1.2 Users and permissions

| Role | Who | Can do | Cannot do |
|---|---|---|---|
| **SME Owner** (authorised approver, rule C05) | Director or person they authorise | Everything for their company; approve listing; accept/decline requests; buy packs; unlist; delete data | — |
| **SME Staff** | Admin / finance staff | Submit bills (eClaim, upload, WhatsApp); fix flagged fields; view results | Approve listing; accept requests; buy packs (can request owner approval) |
| **Investor / Bank** | Subscribed bank, DFI or green investor | Browse anonymised listings; set own criteria; run repayment check on own terms; request to connect; send EOI after acceptance | See company identity before acceptance; see any score or rating (none exist) |
| **Supplier** | SEDA-registered PV provider, LED or aircon supplier | See listings in own category and service area; send proposal request (limit 5/week); send firm quotation after acceptance | See other suppliers' quotes or prices; see identity before acceptance |
| **Orbyte Ops** (internal, optional in demo) | Orbyte staff | Review queue, tariff parameters, audit log, module metrics | Approve on behalf of an SME |

### 1.3 Orbyte features the UI reuses

| Orbyte feature | Where it appears in GreenReady |
|---|---|
| **Connect** (sign-in, roles, approval workflows) | Login, role switcher, every Approve / Accept action |
| **Credit wallet** (one wallet for all modules) | Wallet balance in the top bar; charge confirmations for analyses (RM2) and Preparation Packs (RM79); RM10 free credit |
| **eClaim** | "TNB bill" claim category; a submitted claim triggers analysis automatically |
| **eSign** | Owner signs the supplier's firm quotation |
| **Audit log** | Activity log timeline on every object (bill, listing, request) |
| **Insights / Marketplace** (planned by Orbyte) | Shown only as "Coming soon" badges — do not fake them |

### 1.4 Pricing the UI must show

| Item | Price | Paid by | Paid how | UI moment |
|---|---|---|---|---|
| Free starting credit | RM10 once (= 5 analyses) | Orbyte gives | Credit wallet | First open of GreenReady; one per SSM number |
| Bill analysis | RM2 per bill | SME | Credit wallet | After the free credit is used; confirm before charging |
| Preparation Pack + 90-day partner access | RM79 per pack | SME (owner only) | Credit wallet | "Prepare pack" button on an upgrade option |
| Supplier connection | RM200 per accepted connection | Supplier | Monthly invoice | Shown to the supplier before sending a request; charged only after the owner accepts |
| Bank / investor subscription | RM2,500 per month | Bank / investor | Monthly invoice | Partner billing page |

Not charged: viewing results already paid for, accepting/declining, browsing, unlisting. **No SME monthly fee, no per-seat fee.** Loans and upgrade payments never pass through Orbyte.

---

## 2. Design system

### 2.1 Colour palette (provided)

| Token | Name | Hex | Role |
|---|---|---|---|
| `--gr-midnight` | Midnight | `#081F5C` | Primary text, headings, top bar, dark hero cards, primary chart series |
| `--gr-royal` | Royal | `#334EAC` | Brand / primary action (buttons, links, active nav, focus ring), accent numbers |
| `--gr-china` | China | `#7096D1` | Secondary chart series, icons on light backgrounds, progress fills, decorative only for text |
| `--gr-sky` | Sky | `#BAD6EB` | Borders of selected cards, tertiary chart series, dividers on dark cards |
| `--gr-dawn` | Dawn | `#D0E3FF` | Info / selected backgrounds, highlighted table row, chips, icon discs |
| `--gr-porcelain` | Porcelain | `#EDF1F6` | App background (page), table zebra rows |
| `--gr-moon` | Moon | `#F7F2EB` | Disclaimer and "estimate" notice boxes |
| `--gr-jicama` | Jicama | `#FFF9F0` | Document previews (Preparation Pack, EOI, proposal) to feel like paper |
| `--gr-asian-pear` | Asian Pear | `#F2F0DE` | "Draft / not yet approved" backgrounds, warning-neutral states |
| `--gr-white` | White | `#FFFFFF` | Cards, inputs, modals |

**Contrast rules (WCAG 2.1, checked):**

| Pair | Ratio | Allowed use |
|---|---|---|
| Midnight on White / Porcelain / Dawn / Jicama / Moon / Asian Pear | 11.8–15.4 : 1 | All text |
| Royal on White / Porcelain / Jicama / Moon | 6.5–7.4 : 1 | All text, links, buttons |
| White on Royal | 7.4 : 1 | Primary button text |
| White on Midnight | 15.4 : 1 | Dark card text |
| Royal on Dawn | 5.7 : 1 | Chip / selected text |
| **China on White** | **3.0 : 1** | **Large text (≥ 24 px) or icons only — never body text** |
| China on Porcelain / Dawn / Sky | < 3 : 1 | Decorative only |

**Functional colours (added — the palette has no status colours):** keep them muted and use them only for status, never for decoration.

| Token | Hex | Use | Contrast on White |
|---|---|---|---|
| `--gr-success` | `#1F7A4D` | Check passed, accepted, live | 5.3 : 1 |
| `--gr-warning` | `#8A5A00` | Spike alert, estimated reading, expiring access | 5.9 : 1 |
| `--gr-danger` | `#B42318` | Check failed, declined, unlist / delete | 6.6 : 1 |
| `--gr-muted` | `#5E6B8A` | Secondary text, captions, timestamps | 5.3 : 1 |
| `--gr-border` | `#D5DCE7` | Input and card borders | — |

Pair every status colour with an icon and a word (e.g. ✓ Passed, ⚠ Spike +19%) — never colour alone.

**Usage proportions:** Porcelain background ~60%, White cards ~25%, Midnight text and dark cards ~10%, Royal accents ~5%. Warm neutrals (Moon, Jicama, Asian Pear) are for documents and notices only.

### 2.2 Typography — Inter

Load Inter from Google Fonts (`wght@400;500;600;700`) with `font-feature-settings: "tnum" 1` on all numbers (tabular figures so RM and kWh columns line up).

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| Display | 32 / 40 | 700 | Big stat numbers (RM2,140, 8/8) |
| H1 | 24 / 32 | 700 | Page title |
| H2 | 20 / 28 | 600 | Section title |
| H3 | 16 / 24 | 600 | Card title |
| Body | 14 / 22 | 400 | Default text |
| Body strong | 14 / 22 | 600 | Labels, table first column |
| Small | 12 / 18 | 400 | Captions, helper text, timestamps |
| Overline | 11 / 16, +0.06em, uppercase | 600 | Section labels ("PRIMARY USER", "ESTIMATE") |
| Mono numbers | Inter with `tnum` | 500 | Tables of RM / kWh |

Sentence case everywhere. No full stops in titles or buttons.

### 2.3 Spacing, radius, elevation, grid

- **Spacing scale (px):** 4, 8, 12, 16, 24, 32, 48. Card padding 24; gap between cards 16; section gap 32.
- **Radius:** inputs and buttons 8; cards 12; chips and pills 999; modals 16.
- **Elevation:** cards `0 1px 2px rgba(8,31,92,.06), 0 4px 12px rgba(8,31,92,.06)`; modals `0 12px 32px rgba(8,31,92,.18)`. No other shadows.
- **Grid:** 12 columns, 1200 px max content width, 24 px gutters. Left nav 240 px (collapses to icons at < 1024 px).
- **Icons:** one outline set only (Lucide or Tabler), 20 px in UI, 1.75 stroke, Royal or Midnight. Icon discs: 40 px circle, Dawn background.

### 2.4 Components (build once, reuse)

| Component | Variants / notes |
|---|---|
| **Button** | Primary (Royal fill, white text) · Secondary (white, Royal border) · Tertiary (text link) · Danger (Danger text, used for Unlist / Delete) · Loading state with spinner · Disabled 40% opacity |
| **Input / Select / Radio / Checkbox** | 40 px height, Border token, Royal focus ring 2 px; helper text below in Muted |
| **Confidence field** | Value + small bar + % (e.g. "4,420 kWh · 97%"); < 85% turns Warning with "Check this" link |
| **Check row** | Icon (✓ / ✗) · rule name · expected vs found · Pass/Fail chip |
| **Stat tile** | Overline label, Display number, Small caption; optional trend arrow |
| **Upgrade option card** | Name, cost, yearly saving, payback, CO2e, "exact" / "estimate" chip, Prepare pack button |
| **Listing card** | Listing ID, sector, state, bands, evidence badge, criteria match, button (role-specific) |
| **Evidence badge** | "6 months of bills · actual readings · 8/8 checks ✓ · quote ✗" |
| **Request card** | Partner type, name (partner's own name is visible to the SME), message preview, Accept / Decline |
| **Wallet chip** (top bar) | "Credit RM6.00" + top-up link; turns Warning below RM4 |
| **Charge confirmation modal** | "This uses RM2 from your Orbyte credit wallet. Balance after: RM4.00" · Confirm / Cancel |
| **Approval modal** (Orbyte Connect) | Shows exactly what will be shared, who sees it, and that it can be undone; requires owner role |
| **Timeline / activity log** | Time · user · role · action · object; filters by object |
| **Disclaimer box** | Moon background: "Estimates for preparation only. Not financial advice." |
| **Document preview** | Jicama background, A4 ratio, for Preparation Pack, EOI and supplier proposal |
| **Empty state** | Icon disc + one sentence + one action |
| **Toast** | Success / Warning / Danger, 4 s, with Undo where possible |
| **Chart** | Bar (monthly usage), line (6–12-month trend), grouped bar (upgrade comparison). Midnight = this month / main series, China = history, Sky = comparison; values labelled on bars; one accent only |

---

## 3. Information architecture

### 3.1 App shell (Orbyte frame)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Orbyte logo │ Module switcher: People · Work · eSign · GreenReady ▾ │ Credit RM6.00 │ 🔔 │ Kilang Contoh (Owner) ▾ │
├──────────────┬───────────────────────────────────────────────────────┤
│ GreenReady   │                                                       │
│  Home        │                 page content                          │
│  Bills       │                                                       │
│  Upgrades    │                                                       │
│  Pack & List │                                                       │
│  Requests (2)│                                                       │
│  Activity    │                                                       │
│  Wallet      │                                                       │
│  Settings    │                                                       │
└──────────────┴───────────────────────────────────────────────────────┘
```

- **Demo role switcher** in the profile menu: SME Owner · SME Staff · Investor (Bank Hijau) · Supplier (Suria Hijau Solar) · Orbyte Ops. Label it "Demo mode" so judges know it is intentional.
- Breadcrumb under the top bar: `GreenReady / Bills / Sep 2026`.

### 3.2 Navigation per role

| SME Owner | SME Staff | Investor | Supplier | Orbyte Ops |
|---|---|---|---|---|
| Home | Home | Opportunity Board | Opportunity Board | Review queue |
| Bills | Bills | My criteria | My requests | Tariff parameters |
| Upgrades | Review queue | Connections | Accepted leads | Audit log |
| Pack & Listing | Activity | Billing | Billing (connection fees) | Module metrics |
| Requests | | Profile | Profile (SEDA no., categories, area) | |
| Activity · Wallet · Settings | | | | |

### 3.3 Route map (suggested)

| Route | Screen |
|---|---|
| `/login` | Orbyte Connect sign-in (mock) |
| `/onboarding` | Company profile (SSM) → 4 questions → free credit |
| `/sme/home` | SME dashboard |
| `/sme/bills`, `/sme/bills/new`, `/sme/bills/:id` | Bill inbox, upload, bill result |
| `/sme/review/:id` | Extraction review (staff) |
| `/sme/upgrades` | Upgrade comparison |
| `/sme/pack/:id` | Preparation Pack builder and preview |
| `/sme/listing/:id` | Listing preview and approval |
| `/sme/requests`, `/sme/requests/:id` | Requests inbox and detail |
| `/sme/activity`, `/sme/wallet`, `/sme/settings` | Log, wallet, privacy |
| `/investor/board`, `/investor/listing/:id`, `/investor/criteria`, `/investor/connections`, `/investor/eoi/:id` | Investor flows |
| `/supplier/board`, `/supplier/listing/:id`, `/supplier/proposal/:id`, `/supplier/leads` | Supplier flows |
| `/ops/review`, `/ops/parameters`, `/ops/audit`, `/ops/metrics` | Orbyte Ops |

---

## 4. Screens in detail

> Every screen lists: **purpose · layout · content · actions · states**. Rule IDs refer to the GreenReady Rules Engine workbook.

### A. Entry and onboarding

**A1. Sign in (Orbyte Connect, mocked)**
- Purpose: show GreenReady reuses Orbyte login and roles.
- Content: Orbyte logo, "Sign in with Orbyte", demo account picker (5 roles).
- State: wrong role → "Ask your company owner to add you".

**A2. Company profile (from SSM)**
- Pre-filled read-only fields: company name, registration no., incorporation date, type, status, nature of business / MSIC, directors, state.
- Derived chips: Active ✓ (C01), Company age band (C02), Size class Micro/Small (C03), Sector group (C04), Region (C06).
- Duplicate check message if SSM no. already exists (C07): "This company already has a GreenReady account. Ask the owner for access."
- Action: Continue.

**A3. Four quick questions** (owner form)
1. Lighting type: Fluorescent / LED / Not sure
2. Aircon type: Non-inverter / Inverter / Mixed / Not sure (+ number of units)
3. Roof access for solar: Yes / No / Not sure
4. Daytime operation: Yes / No (pre-filled from Orbyte attendance if available, editable)
- One question per row, big radio cards, progress "2 of 4".

**A4. Free credit welcome**
- "RM10 free credit added to your Orbyte wallet — enough for 5 bill analyses."
- Three ways to send a bill (cards): **Claim it in eClaim** · **Forward on WhatsApp** · **Upload here**.
- Action: Upload first bill.

### B. SME Owner and Staff

**B1. Home dashboard** (owner and staff)
- Row 1 stat tiles: This month's bill (RM2,140, due 10 Nov 2026) · Usage (4,420 kWh, ⚠ +19% vs 6-month average) · Bill check (8/8 ✓) · Real cost per kWh (RM0.51).
- Row 2: 6-month usage chart (bars, this month in Midnight, history in China) + "What changed" panel (B03 spike, B06 rebate-band warning, B08 trend).
- Row 3: Best upgrade teaser ("LED pays back in about 1.2 years") → View upgrades; Requests waiting (2) → Review; Credit chip.
- Empty state (no bill yet): "Send your first TNB bill to see your check in about 3 minutes."

**B2. Bills inbox**
- Table: month · source (eClaim / WhatsApp / Upload) · amount · usage · checks (8/8 ✓ or 7/8 ✗) · status (Ready / Needs review / Processing / Estimated reading) · charged (Free / RM2.00).
- Filter by status; search by month.
- Badge on rows that arrived from eClaim: "From eClaim".

**B3. Add a bill**
- Drop zone (PDF, JPG, PNG, screenshot), camera button on mobile.
- Before upload: credit notice — "Free (3 of 5 free analyses left)" or "RM2.00 from your wallet" → charge confirmation modal.
- Processing state with steps: Reading bill (AI) → Checking against tariff (rules) → Building insights. Show elapsed time (target < 60 s).
- Errors: unreadable file → "We couldn't read this. Try a clearer photo or enter it manually" (manual entry form); unknown tariff (V13) → manual entry.

**B4. Extraction review** (staff; the hardest-risk fallback)
- Left: bill image with highlighted boxes. Right: extracted fields with confidence (B01–B23: account last-4, tariff, billing period, previous/current reading, kWh, energy, capacity, network, AFA, retail, rebate, KWTBB, service tax, current charges, previous balance, total due, due date, reading type).
- Fields under 85% (V12) in Warning with "Check this"; failed checks listed at top.
- Actions: Correct value · Confirm all · Switch to manual entry. Every change logged (M06).
- No calculation runs until all flags are cleared (V12).

**B5. Bill result**
- Header: month, amount, due date, reading type badge (Actual / Estimated — V11).
- **8 checks panel** (V01–V09 summarised as 8 rows): meter reading, energy, capacity, network, rebate, usage subtotal, KWTBB 1.6%, total. Each row: expected vs found, ✓/✗.
- Insight cards: daily usage (B01), baseline (B02), spike (B03), real cost per kWh (B04), variable share (B05), rebate-band warning (B06), marginal saving rate (B07), trend (B08).
- Charge breakdown table (energy, capacity, network, AFA, retail, rebate, KWTBB, service tax) with "What is this?" tooltips in plain English.
- Footer: Disclaimer box; "Charged: Free" / "RM2.00".

**B6. Upgrade comparison** ★ most important feature
- Intro line: "Same formulas for every option. No supplier is paying for this ranking."
- Option cards side by side (only those that pass S01–S03; S04 "Monitor only" if none):

| Field | LED (40 tubes) | Inverter aircon (3 units) | Rooftop solar (≈23 kWp) |
|---|---|---|---|
| Cost | ≈RM1,600 (estimate) | ≈RM6,600 (estimate) | ≈RM46,000 (estimate) |
| Saving / year | ≈RM1,370 | ≈RM1,600 | ≈RM15,450 |
| Payback | ≈1.2 years | ≈4.1 years | ≈3 years |
| CO2e / year | ≈2.0 t | ≈2.3 t | ≈22.6 t |
| Basis | U01, U05–U09 | U02 | U03–U04 |

- Grouped bar chart: yearly saving vs cost per option.
- "How we calculated this" expander showing the formula and parameter values (tariff RM0.5068/kWh, grid factor 0.740 kg/kWh, solar yield 1,320 kWh/kWp) with sources.
- Each card: chip "estimate" (benchmark price) or "exact" (valid quote attached, V14–V15); button **Prepare pack** (owner) or **Ask owner** (staff).
- Optional: "Attach a supplier quote" upload → re-runs U09 with exact CapEx.

**B7. Preparation Pack builder**
- Step 1 choose upgrade(s) to include (tick list).
- Step 2 review contents: 6-month bill summary, checks passed, upgrade estimates, evidence badge, company profile summary.
- Step 3 charge confirmation: "RM79 from your Orbyte credit wallet. Includes listing and 90 days of investor and supplier connections."
- Preview: Jicama A4 document with Approve / Edit / Cancel. Download PDF.

**B8. Listing preview and approval** (human control point 1)
- Split view: "What you see" vs **"What partners see"** (anonymised card from L01–L05).
- Clear list of what is hidden: company name, registration no., address (state only), contact details, director names, exact kWh and RM, bill files.
- Upgrade tags to publish (from F08).
- Approval modal (Orbyte Connect approval): "Publish anonymously to the Opportunity Board for 90 days?" · Approve / Cancel. Only the owner role sees Approve (C05).
- After approval: status Live, listing ID (GR-L-0871), expiry date, views counter (e.g. 18 investors, 9 suppliers), Unlist button (Danger, M07).

**B9. Requests inbox** (human control point 2)
- Cards: Bank Hijau (Investor) — EOI waiting; Suria Hijau Solar (Supplier) — outreach proposal (indicative RM43k–47k).
- Detail view: partner profile (SEDA no. for suppliers), their message, what they will receive if accepted (full pack, company name, contact person, site address, exact usage).
- Actions: **Accept** (approval modal) · **Decline** (optional reason) · Ask a question.
- After accept: identity revealed to that partner only (M05); supplier is charged RM200 (shown as info, not to the SME).

**B10. Quotation and eSign**
- When a supplier sends a firm quotation: preview with V14/V15 checks (validity, SEDA no., arithmetic) and a compare button (re-runs Upgrade comparison with exact CapEx).
- Action: **Sign with Orbyte eSign** (mock) → signed copy + audit entry. Note: "Payment and installation are agreed directly with the supplier."

**B11. Activity log** (logged outcome)
- Timeline: "10:02 Siti (Staff) submitted Sep bill via eClaim · 10:03 AI read 23 fields (2 flagged) · 10:05 Siti fixed 2 fields · 10:06 8/8 checks passed · 10:20 Ahmad (Owner) bought Preparation Pack (RM79) · 10:21 Ahmad approved listing GR-L-0871 · 13:20 Suria Hijau Solar sent request · 13:45 Ahmad accepted".
- Filter by object, user, date. Export CSV.

**B12. Wallet**
- Balance, free analyses left, transactions (Free credit +RM10, Analysis −RM2, Pack −RM79), Top up (link to Orbyte wallet — mocked).
- Low balance state: "RM2 left — enough for 1 analysis."

**B13. Settings and privacy**
- PDPA consent record (date, version), data retention period, notification preferences (in-app, email, WhatsApp).
- Danger zone: Unlist all listings · Delete my GreenReady data (with confirmation and the retention note).
- Team members and roles (links to Orbyte Connect).

### C. Investor / Bank

**C1. Opportunity Board**
- Filters (investor's own criteria, M02): sector, state, upgrade type, CapEx band, minimum yearly saving, company age, payback under X years. Save as "My criteria".
- Sort: newest first only (M03) — no "best" or "score" sort. Show the note: "Listings are not scored or ranked."
- Listing cards: ID, sector, state, size, age band, upgrade wanted, usage band, bill band, CapEx band, estimated saving, payback, CO2e, evidence badge, criteria match "5 of 5 ✓", listed date, Request to connect.

**C2. Listing detail (before acceptance)**
- All card fields + **Repayment check on your own terms**: inputs loan amount, tenor, rate (investor types it) → output "about 1.4× savings coverage". Label: "Your terms, your decision. GreenReady does not assess credit."
- Hidden section with lock icons (company name, reg no., address, contacts, exact figures, bill files).
- Action: Request to connect → modal with optional message.

**C3. Connections**
- Status: Requested · Accepted · Declined · Expired.
- Accepted → unlocked Preparation Pack, 6 months of bills, SSM profile, quotes; **Send EOI** button.

**C4. EOI draft**
- Pre-filled non-binding Expression of Interest (Jicama document): bank name, listing, indicative amount range, tenor range, conditions ("subject to the bank's own assessment"), contact. Investor edits fields in brackets. Send → appears in SME Requests.

**C5. Billing**
- Plan: RM2,500 per month, next invoice date, invoices list (mock).

### D. Supplier

**D1. Opportunity Board (filtered)**
- Automatically filtered by the supplier's categories and service area (M01); badges "inside your service area ✓", "matches your category ✓".
- Card fields: ID, sector, state, upgrade wanted, usage band, daytime operation, suggested size (≈23 kWp), lighting type, CapEx band, existing quote (none / yes), evidence badge, listed date, **requests left this week 3 of 5** (M04).

**D2. Send proposal**
- Pre-filled outreach proposal (Jicama document) from the listing facts and GreenReady estimate; supplier edits bracketed fields (price range, warranties, timeline).
- Fee notice before sending: "You pay RM200 only if the owner accepts."
- Send → appears in SME Requests.

**D3. Accepted leads**
- Unlocked: company name, contact person, site address, exact usage for sizing; **Send firm quotation** (upload or form; checked by V14–V15).

**D4. Billing**
- Accepted connections × RM200, monthly invoice (mock).

### E. Orbyte Ops (optional for demo, useful for Q&A)

- **Review queue:** bills with flagged fields, age, assignee.
- **Tariff parameters:** P01–P40 table (TNB rates, KWTBB 1.6%, service tax 8%, grid factor 0.740, confidence threshold 85%, spike threshold, request limit 5/week) — read-only in demo.
- **Audit log:** all events across companies.
- **Module metrics:** active SMEs, bills analysed, packs, listings, connections, credit spent, partner fees — label "synthetic demo data".

---

## 5. Key flows (demo path)

**Flow 1 — Bill to result (trigger → data → logic)**
1. Staff submits the TNB bill in eClaim (mock) → GreenReady receives it (badge "From eClaim").
2. AI reads the bill; 2 fields under 85% → Review queue.
3. Staff fixes them → 8/8 checks pass → result with spike alert +19%.
4. Wallet shows "Free (4 of 5 left)".

**Flow 2 — Upgrade decision**
5. Owner opens Upgrade comparison → sees LED, aircon, solar side by side → expands "How we calculated this".

**Flow 3 — Pack and listing (human approval 1)**
6. Owner prepares a pack (RM79 confirmation) → previews → approves listing → anonymous card goes live as GR-L-0871.

**Flow 4 — Partners (human approval 2)**
7. Switch to Supplier: listing visible in area → send proposal (fee notice).
8. Switch to Investor: filter by own criteria → repayment check on own terms → request to connect.
9. Switch back to Owner: Requests (2) → accept both → identities revealed to those two only.
10. Investor sends EOI; supplier sends firm quotation; owner signs with eSign.

**Flow 5 — Logged outcome**
11. Activity log shows every step with user, role and time.

**Fallback flow (hardest risk):** upload a blurred bill → "couldn't read" → manual entry form → checks still run.

**Edge states to build:** no bill yet · estimated reading (excluded from spike) · failed check (shows expected vs found, sends to review) · unknown tariff · out of credit · listing expired after 90 days · request limit reached · partner declined · company not active (C01 blocks listing) · staff tries to approve (blocked with explanation).

---

## 6. Copy, compliance and trust

- **Disclaimer (on every estimate, pack, listing, EOI, proposal):** "Estimates for preparation only. Not financial advice."
- **Never show:** credit scores, ratings, "approval chance", loan recommendations, or "best investor".
- **Always show:** who will see what before any share; that the owner can unlist at any time; data source and date for tariff and grid factor.
- **Money:** "Loans and upgrade payments are agreed directly with the bank or supplier. They never pass through Orbyte."
- **PDPA:** consent at onboarding; data minimised on listings (state only); retention period shown in Settings.
- **AI labelling:** fields read by AI show a small "AI" tag and confidence; calculations show "Rule" with the rule ID on hover.
- **Tone:** plain English, short sentences, numbers with units (RM, kWh, t CO2e, years). Optional BM labels later.

---

## 7. Synthetic demo data

| Item | Value |
|---|---|
| Company | Kilang Contoh Sdn Bhd (fictional), Selangor, manufacturing, Small, 5–10 years, Active |
| Users | Ahmad (Owner), Siti (Staff) |
| Listing ID | GR-L-0871 |
| This month's bill | RM2,140 · 4,420 kWh · due 10 Nov 2026 · Actual reading |
| Spike | +19% vs 6-month average |
| Checks | 8/8 passed (after 2 fields fixed) |
| Real cost per kWh | RM0.51 |
| 6-month history | Apr–Sep kWh values that average ≈3,715 (so Sep is +19%) |
| Options | LED ≈RM1,600 / RM1,370 yr / 1.2 yr / 2.0 t · Inverter aircon ≈RM6,600 / RM1,600 yr / 4.1 yr / 2.3 t · Solar 23.1 kWp ≈RM46,000 / RM15,450 yr / ≈3 yr / 22.6 t |
| Investor | Bank Hijau Berhad (fictional), criteria: solar · Selangor · RM20k–50k · 5+ years · payback < 5 years → 5 of 5 ✓ |
| Repayment check | RM45,000 · 5 years · [investor's rate] → ≈1.4× savings coverage |
| Supplier | Suria Hijau Solar Sdn Bhd (fictional), SEDA RPVSP [no.], Selangor, solar + LED; proposal RM43k–47k (Option A), RM50k–55k (Option B) |
| Wallet | RM10 free credit → 5 analyses; then RM2 each; Pack RM79 |
| Second sample bill | The real TNB domestic sample (passes 8/8) for the "any format" demo |

All names are fictional; mark every screen footer "Demo — synthetic data".

---

## 8. Responsive and accessibility

- **Breakpoints:** ≥ 1280 desktop (main demo) · 1024 tablet (nav collapses) · ≤ 640 mobile (bill upload, results, requests, approve — owners act on phones).
- Touch targets ≥ 44 px; focus ring Royal 2 px with 2 px offset; full keyboard path through the demo flow.
- Text contrast per §2.1; never China for body text.
- Charts: values labelled, not colour-only; `aria-label` with the finding ("September usage 19% above average").
- Respect `prefers-reduced-motion`; no auto-playing animation.
- Numbers use tabular figures; dates `10 Nov 2026`; money `RM2,140`.

---

## 9. Technical approach and deployment

### 9.1 Stack (as declared in the proposal)

| Layer | Tool | Notes |
|---|---|---|
| Front end | React / Next.js (or Vite + React) with Tailwind; Inter via Google Fonts | Tailwind theme uses the tokens in §2 |
| Back end / agents | FastAPI + LangGraph on Replit | Orchestrates read → validate → calculate → list |
| Document AI | Vision-language model on RunPod Serverless | Returns fields + confidence; never calculates |
| Rules engine | Python module from the Rules Engine workbook (V, C, B, S, U, L, M rules; P parameters) | Deterministic; unit-tested against the Worked_Example sheet |
| Database / auth / storage | Supabase (Postgres, Storage, Row Level Security) | Orbyte Connect and wallet mocked as tables |
| Messaging | WhatsApp via Whapi | Forward bill → summary reply |
| Charts | Recharts or Chart.js | Palette per §2.4 |
| PDF | Server-side HTML → PDF for Preparation Pack, EOI, proposal | Jicama paper style |

### 9.2 Core data tables (Supabase)

`companies` (SSM fields, status, size, sector, state) · `users` (role, company_id) · `bills` (source, file, status, reading type) · `bill_fields` (field, value, confidence, corrected_by) · `checks` (rule_id, expected, found, pass) · `insights` · `upgrade_options` (type, capex, saving, payback, co2e, basis exact/estimate) · `packs` · `listings` (bands, tags, status, expiry) · `partners` (type, categories, area, SEDA no.) · `requests` (partner, listing, status, message) · `documents` (EOI, proposal, quotation, signed) · `wallet_ledger` (amount, reason) · `audit_log` (user, role, action, object, time) · `parameters` (P01–P40).

RLS: SMEs see only their company; partners see only anonymised listing views until `requests.status = accepted`.

### 9.3 API endpoints (minimum)

`POST /bills` (upload / eClaim webhook / WhatsApp webhook) · `GET /bills/:id` · `PATCH /bills/:id/fields` · `POST /bills/:id/validate` · `GET /upgrades?company=` · `POST /packs` · `POST /listings/:id/approve` · `GET /board` (role-filtered) · `POST /requests` · `POST /requests/:id/accept|decline` · `POST /documents/eoi|proposal|quotation` · `POST /esign/:doc` (mock) · `GET /audit` · `GET /wallet` · `POST /wallet/charge`.

### 9.4 Deployment checklist

- [ ] Public live URL (Replit deployment or Vercel front end + Replit API); works without login friction — demo accounts on the sign-in screen
- [ ] Seed script loads the synthetic demo data in §7; a **Reset demo** button in Ops
- [ ] Public GitHub repo with README: setup, env vars (no secrets committed), architecture diagram, rule list, demo accounts, AI declaration
- [ ] Rules engine unit tests pass against the Worked_Example sheet (sample bill 8/8)
- [ ] Timings measured for the deck: bill → result (target < 60 s), manual check vs GreenReady (target 20 min → 3 min)
- [ ] Extraction accuracy on 10 test bills recorded
- [ ] Error handling: VLM timeout → retry once → manual entry
- [ ] HTTPS, no real personal data, "Demo — synthetic data" footer
- [ ] Mobile check on the upload → result → approve path
- [ ] Tech & Tools Declaration lists every API, model, dataset and AI tool used (including AI coding assistants)

---

## 10. Demo video script (5–7 minutes, prototype shown live)

| Time | Show | Say (key line) |
|---|---|---|
| 0:00–0:40 | Problem slide | "Every month an SME gets a TNB bill that nobody checks." |
| 0:40–1:40 | eClaim → review queue → 8/8 checks | Trigger, connected data, decision logic; AI reads, rules decide; low-confidence fields go to staff |
| 1:40–2:40 | Upgrade comparison + formula expander | Most important feature: same formulas, no seller bias |
| 2:40–3:30 | Pack (RM79 confirm) → listing approval → anonymous card | Human approval 1; what partners can and cannot see |
| 3:30–4:30 | Supplier view → proposal; Investor view → criteria + repayment check | Fair chance for every partner; no scores |
| 4:30–5:10 | Owner accepts both → identity revealed only to them → eSign | Human approval 2 |
| 5:10–5:40 | Activity log | Logged outcome |
| 5:40–6:30 | Business model + ROI slide | Orbyte earns per use; break-even Year 2; customers gain 161% in Year 1 |
| 6:30–7:00 | Risk + fallback (blurred bill → manual entry) | Hardest risk and its fallback, live |

---

## 11. Out of scope for the prototype

Real Orbyte API integration (mocked), real payments and top-ups, Sabah and Sarawak tariffs, smart-meter feeds, motors and chillers, loan applications, credit scores or ratings, real customer data, supplier bidding marketplace, Insights and Marketplace (Orbyte roadmap).

---

## 12. Acceptance checklist (done when…)

- [ ] A judge can complete Flows 1–5 on the live link in under 7 minutes
- [ ] Owner approval is required for listing and for every connection; staff cannot approve
- [ ] Partners never see identity before acceptance; no score or ranking appears anywhere
- [ ] Every number on the result and comparison screens traces to a rule ID and parameter
- [ ] Wallet charges match pricing (free 5 → RM2 → RM79 pack); partner fees shown to partners only
- [ ] Activity log records every step
- [ ] Colours and Inter typography follow §2; contrast checks pass
- [ ] Figures match the deck, proposal and financial projection

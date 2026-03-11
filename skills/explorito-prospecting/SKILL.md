---
name: explorito-prospecting
description: B2B prospecting SDR workflow for Munily (propiedad horizontal) to find, qualify, score, and register ICP companies in HubSpot across Colombia, Panamá, and the United States. Use when you need to: (1) search the web/Google/Google News and browse sites to extract company data, (2) use LinkedIn Sales Navigator to find companies and decision makers, (3) apply Munily ICP rules and lead scoring threshold (score mayor o igual a 40) with strict disqualification rules, (4) deduplicate against HubSpot before creation, (5) create HubSpot company/contact/note records via API, (6) keep session logs and produce an end-of-session report.
---

# Explorito Prospecting (Munily SDR)

## Operating rules (non-negotiable)

- Never create anything in HubSpot without:
  1) ICP segment match, 2) score >= 40, 3) verifiable digital presence, 4) duplicate check.
- Never invent data. If unknown: leave empty or write `Por verificar`.
- Always store at least one source URL in the HubSpot note.
- If there is doubt, discard.

## Required inputs (ask user once, then proceed)

1. **HubSpot Private App token** (scope: CRM objects: companies, contacts, notes; search).
2. **HubSpot property mapping** (see `references/hubspot-field-mapping.md`).
3. **LinkedIn Sales Navigator access** in a real browser tab (Chrome Relay attached).
4. Optional: user-provided ICP / scoring docs (store in `references/` and reference them).

## Workflow (follow exactly)

### Step 0 — Start session

- Create a session id (timestamp-based), and a JSONL log file:
  - `automation/explorito/logs/<session-id>.jsonl`
- Track counters for report (found, discarded by reason, saved, by country/segment, avg score).

Use scripts:
- `scripts/session_log.py` (append + report)

### Step 1 — Identification

For each candidate company:
- Capture:
  - name
  - source type (LinkedIn | Google | Directorio | Noticias)
  - source URL
  - country/city if stated

Log event: `identified`.

### Step 2 — Investigation (evidence-first)

Gather evidence from **at least one** of:
- Official website (About/Services/Projects/Clients pages)
- LinkedIn company page (industry, size, locations, activity)
- News / press / directories

Extract into a structured object using the schema in:
- `references/company-schema.json`

Log event: `researched`.

### Step 3 — ICP classification

Classify into exactly one segment:
- `Administración PH`
- `Seguridad Privada`
- `Constructora`

Disqualify if:
- Not in the 3 segments, OR
- <5 employees (or clearly micro), OR
- Not operating in CO/PA/US, OR
- Inactive >2 years, OR
- No verifiable digital presence.

Log event: `discarded` with reason, or `icp_matched`.

### Step 4 — Lead scoring

Compute score with `scripts/lead_scoring.py` using the rules in:
- `references/lead-scoring.md`

If score < 40: discard.

Log event: `scored` and possibly `discarded`.

### Step 5 — Duplicate check (HubSpot)

Before creating anything, check HubSpot by:
1) domain (preferred)
2) company name (fallback)

Use:
- `scripts/hubspot_crm.py search-company --domain <domain>`
- `scripts/hubspot_crm.py search-company --name <name>`

If exists: discard as duplicate.

Log event: `duplicate_found`.

### Step 6 — Prepare HubSpot payload

Populate the payload fields (leave unknown as empty/`Por verificar`):
- Company:
  - Nombre
  - Dominio
  - Sector (Real Estate | Security | Construction)
  - Tipo = Cliente potencial
  - Ciudad, Región/Estado, País, Código postal
  - Empleados (estimado)
  - Ingresos (estimado)
  - Zona horaria
  - Descripción (2–3 frases, why ICP)
  - LinkedIn company URL
  - Propietario (CO equipo Colombia | PA equipo Panamá | US equipo USA)
  - Lead Score
  - Segmento ICP
  - Fuente del lead
- Contact (if decisor identified):
  - Nombre completo, cargo, email (if available), LinkedIn URL

Follow mapping:
- `references/hubspot-field-mapping.md`

Log event: `hubspot_payload_ready`.

### Step 7 — Create records in HubSpot

1) Create company
2) Create contact (optional) + associate to company
3) Store evidence in Company properties (preferred in this deployment):
   - Write the full traceability block into the Company multiline property `nota`
   - Also set: `source_url`, `lead_source`, `lead_score`, `icp_segmen`, `last_prospected_at`

Use:
- `scripts/hubspot_crm.py create-company --json <file>`
- `scripts/hubspot_crm.py create-contact --json <file>`
- `scripts/hubspot_crm.py associate --from-type contacts --from-id <contactId> --to-type companies --to-id <companyId>`

Log event: `saved_to_hubspot`.

### Step 8 — Log

For each company, append a final decision row:
- saved | discarded
- score
- reason if discarded

## End-of-session report

Generate and print:
- total found
- total discarded + top discard reason
- total saved
- distribution by country
- distribution by segment
- average score (saved)
- top 3 most promising
- best-performing sources

Use:
- `scripts/session_log.py report --session <session-id>`

## Browser automation notes (LinkedIn / Google)

- Use the Browser tool when available.
- For LinkedIn Sales Navigator, prefer a user-authenticated Chrome tab (Chrome Relay attached). Avoid storing credentials in files.
- Extract only what is visible/allowed; respect ToS and rate limits.

## Files in this skill

- `scripts/lead_scoring.py` — deterministic scoring + disqualification checks
- `scripts/hubspot_crm.py` — HubSpot search/create (companies/contacts/notes)
- `scripts/session_log.py` — JSONL logging + session report
- `references/lead-scoring.md` — scoring rules (authoritative)
- `references/hubspot-field-mapping.md` — property mapping template
- `references/company-schema.json` — structured extraction schema

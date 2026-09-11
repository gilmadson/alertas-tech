# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlertasTech is a static landing page that lets users subscribe to tech deal alerts via WhatsApp or Telegram groups. It monitors product prices on Mercado Livre, Amazon, Magalu (Magazine Luiza), Shopee, AliExpress and KaBuM! and sends notifications when discounts reach ≥15%.

## Architecture

Single-file static site (`index.html`) deployed on Vercel. No build step, no bundler, no framework.

- **Frontend**: Vanilla HTML/CSS/JS in one `index.html`. Uses Google Fonts (Syne + DM Sans). Mobile-first dark theme.
- **Backend**: Supabase (REST API) for lead storage. Leads are saved via `POST /rest/v1/leads` with anon key auth.
- **Routing**: `vercel.json` rewrites all paths to `index.html` (SPA-style catch-all).

## Key Patterns

- **Category → Group mapping**: `grupos.json` is the single source of truth — 20 entries: the 19 categories the deal engine publishes to, plus `geral` (the engine's super-discount group, which receives by discount size rather than by subject; it is the destination for people who do not want to pick a category). It holds each entry's WhatsApp group JID and the owning OpenWA session UUID. The `GRUPOS` object inside `index.html` lives between the `// GRUPOS:INICIO` and `// GRUPOS:FIM` markers and is **generated** by `scripts/sincronizar_landing.py` — do not hand-edit it. Adding a category requires: an entry in `grupos.json`, a card in the HTML grid (with `data-slug`), and a sync run.
- **Every category takes the same path.** There is no special-case flow — the previous "ofertas gerais" branch hid the form (and with it `#form-aviso`), which brought back the silent failure. A group with no Telegram channel gets `tg: null` and the Telegram button is hidden for it.
- **Anti-drift tests**: `tests/` fails when the landing and `grupos.json` disagree, when a WhatsApp invite is duplicated across categories, when the Supabase key placeholder comes back, or when the consent block disappears. `tests/test_landing_comportamento.py` runs the page's own JS under `node` with a fake DOM.
- **Consent (LGPD)**: submission is blocked until `consent-check` is ticked (never pre-ticked), and the page carries a privacy section (`#privacidade`). The lead is stored with `consentimento: true` and `consentimento_em` = **the instant the box was ticked** (recorded by `marcarConsentimento`, the box's own `onchange`), not the instant of submission. That record is the LGPD legal basis (art. 7, I) and it is also what backs the affiliate links: the Amazon Associates policy only allows such messages when they were requested.
- **Visit origin**: every lead carries `origem`/`meio`/`campanha`. Order: `utm_source|utm_medium|utm_campaign` from the URL → value kept in `sessionStorage` from the first visit → `document.referrer` domain with `meio: 'referrer'` → `origem: 'direto'`. A lead with no origin is what ruins campaign reports, so there is always a value. UTM text comes from the URL and goes to the database: it is filtered by `UTM_ACEITO` and capped at `UTM_MAX` (120), on the way in **and** on the way out of `sessionStorage`, which the visitor can edit. Telemetry is wrapped so it can never cost a signup.
- **Visible failure**: `salvarLead` checks `res.ok`; a failed POST shows `#form-aviso` and keeps the modal open, while the group invite is still delivered. Never go back to swallowing the error.
- **Store selection**: Modal includes checkboxes for Mercado Livre (checked by default), Amazon, Magalu, Shopee, AliExpress and KaBuM!. Users pick which stores they want alerts from. Selected stores are saved as comma-separated values in the `lojas` field on Supabase. Store checkbox IDs live in the `LOJA_IDS` array; adding a store requires: a hero badge, a checkbox in the modal, CSS color classes, and an entry in `LOJA_IDS`.
- **Lead capture flow**: Modal opens on category click → user fills phone (required) + optional name/email → selects stores → "Não sou um robô" checkbox → submit saves to Supabase then redirects to group link.
- **Anti-bot measures**: Honeypot hidden field + minimum time threshold (1.5s). A submission faster than that is **refused with a message** — it must never open the group or close the modal, because that would signal success without a single attempt to store the lead.

## Development

No build step. Open `index.html` in a browser to preview.

```bash
python -m pytest                                    # suite (no network)
python -m coverage run --source=scripts -m pytest && python -m coverage report -m
OPENWA_API_KEY=... python scripts/sincronizar_landing.py --dry-run
```

Deploy is **manual and double**: the Vercel project `alertastech-landing` is not
linked to GitHub, and the same page is also served by GitHub Pages from this
repo. Publishing one and forgetting the other is how they drift apart. See
`README.md`.

## Language

All user-facing text is in Brazilian Portuguese (pt-BR).

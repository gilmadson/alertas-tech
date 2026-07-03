# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlertasTech is a static landing page that lets users subscribe to tech deal alerts via WhatsApp or Telegram groups. It monitors product prices on Mercado Livre and sends notifications when discounts reach ≥15%.

## Architecture

Single-file static site (`index.html`) deployed on Vercel. No build step, no bundler, no framework.

- **Frontend**: Vanilla HTML/CSS/JS in one `index.html`. Uses Google Fonts (Syne + DM Sans). Mobile-first dark theme.
- **Backend**: Supabase (REST API) for lead storage. Leads are saved via `POST /rest/v1/leads` with anon key auth.
- **Routing**: `vercel.json` rewrites all paths to `index.html` (SPA-style catch-all).

## Key Patterns

- **Category → Group mapping**: `GRUPOS` object maps category slugs to WhatsApp/Telegram group links. Adding a new category requires: a card in the HTML grid, an entry in `GRUPOS`, and group links.
- **Lead capture flow**: Modal opens on category click → user fills phone (required) + optional name/email → "Não sou um robô" checkbox → submit saves to Supabase then redirects to group link.
- **Anti-bot measures**: Honeypot hidden field + minimum time threshold (1.5s) before submission is accepted.

## Development

No build or test commands. Open `index.html` in a browser to preview. Deploy happens automatically via Vercel on push.

## Language

All user-facing text is in Brazilian Portuguese (pt-BR).

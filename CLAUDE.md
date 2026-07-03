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

- **Category → Group mapping**: `GRUPOS` object maps category slugs to WhatsApp/Telegram group links. Adding a new category requires: a card in the HTML grid, an entry in `GRUPOS`, and group links.
- **Store selection**: Modal includes checkboxes for Mercado Livre (checked by default), Amazon, Magalu, Shopee, AliExpress and KaBuM!. Users pick which stores they want alerts from. Selected stores are saved as comma-separated values in the `lojas` field on Supabase. Store checkbox IDs live in the `LOJA_IDS` array; adding a store requires: a hero badge, a checkbox in the modal, CSS color classes, and an entry in `LOJA_IDS`.
- **Lead capture flow**: Modal opens on category click → user fills phone (required) + optional name/email → selects stores → "Não sou um robô" checkbox → submit saves to Supabase then redirects to group link.
- **Anti-bot measures**: Honeypot hidden field + minimum time threshold (1.5s) before submission is accepted.

## Development

No build or test commands. Open `index.html` in a browser to preview. Deploy happens automatically via Vercel on push.

## Language

All user-facing text is in Brazilian Portuguese (pt-BR).

# Plano — landings exclusivas (Imperdíveis ML, Super Desconto)

O `<script>` do `index.html` sai para `landing.js` (movido, não reescrito); as
3 páginas incluem por caminho relativo — GitHub Pages serve de
`/alertas-tech/`, absoluto quebraria só lá, calado. 2 fatias, cada uma provada
em produção.

## FATIA 1 — Fundação + Imperdíveis no ar (a menor que já serve)

Entrega: `landing.js` extraído; `index.html` e o novo `imperdiveis.html`
incluem via `<script src="landing.js">`. `imperdiveis.html` chama
`abrirModal` direto — sem grade, sem lojas (é 100% Mercado Livre).
`vercel.json` ganha `/imperdiveis` antes do catch-all; cache no-cache no
`landing.js`. `sincronizar_landing.py` passa a escrever em `landing.js` por
padrão (senão quebra ao atualizar qualquer convite das 20 categorias já
publicadas). Teste novo (regra específica sempre antes do catch-all — já
cobre a fatia 2) e o harness que lia o `<script>` do `index.html` passa a ler
`landing.js`.

Prova: Gilmadson abre `/imperdiveis` no Vercel e no GitHub Pages, completa um
cadastro de teste e confirma que caiu no grupo real; abre `/` e confirma que
nada mudou. ~3-4h.

## FATIA 2 — Super Desconto com página própria

Entrega: `super-desconto.html` (mesmo padrão; corrige o bug do produto — sem
seção de lojas, o cadastro passa a valer qualquer loja, não só Mercado
Livre). `vercel.json` ganha `/super-desconto`. `grupos.json` ganha a lista
nova `exclusivas` (não toca nos testes de `categorias`). `sincronizar_landing.py`
resolve `exclusivas` também.

Prova: cadastro de teste em `/super-desconto` cai no grupo certo; a linha no
Supabase sai com `categoria='super-desconto'` (métrica separada de `geral`) e
`lojas` não é só Mercado Livre. ~1-2h.

## Depende do Gilmadson

- Fatia 1: disparar o deploy manual do Vercel (não linkado ao GitHub) e abrir
  o link.
- Fatia 2, antes de fechar `grupos.json` — pergunta a validar: Super Desconto
  ganha slug/grupo próprio com métrica separada (como desenhado), ou é atalho
  pro MESMO grupo do "geral"? Se atalho, a correção é 1 linha; não bloqueia
  começar a fatia.
- Fatia 2: confirmar que a `OPENWA_API_KEY` está acessível para rodar o sync.

## Ordem, por quê

Extração primeiro por dependência técnica (as páginas novas incluem um
arquivo que ainda não existe) e por mexer na página já em produção.
Imperdíveis antes de Super Desconto por risco: já sincronizado, prova ponta a
ponta sem depender de decisão nenhuma; Super Desconto tem pergunta aberta e
entrada nova no `grupos.json`.

## Fica pra depois

Grade de categorias dentro das páginas exclusivas; uso dos links em campanha
paga (setor de tráfego); reorganizar o card "Ofertas gerais" do `index.html`
— fica como está, só `grupos.json` ganha a entrada nova.

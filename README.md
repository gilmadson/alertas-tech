# AlertasTech — landing

Site estático (sem framework e sem build) que capta quem quer entrar nos grupos
de oferta do AlertasTech.

| Arquivo | O que é |
|---|---|
| `index.html` | a landing completa, com as 21 categorias |
| `imperdiveis.html` | página exclusiva do grupo Imperdíveis ML (`/imperdiveis`) |
| `landing.js` | **toda** a lógica, compartilhada pelas páginas |
| `landing.css` | o tema, compartilhado pelas páginas |

O JS e o CSS saíram de dentro do `index.html` em 18/09/2026, quando nasceu a
segunda página: cópia do mesmo código em duas páginas é como elas ficam
diferentes sem ninguém ver. Duas regras de quem incluir os compartilhados:
**caminho relativo** (`src="landing.js"` — o GitHub Pages serve de
`/alertas-tech/`, e um `/landing.js` quebraria só lá, calado) e o `landing.js`
**no fim do `<body>`**, porque ele lê o `document.body` no carregamento.

Elas estão publicadas em **dois** lugares:

- <https://alertastech-landing.vercel.app> — projeto Vercel `alertastech-landing`,
  **não ligado ao GitHub**: o deploy é manual.
- <https://gilmadson.github.io/alertas-tech/> — GitHub Pages, servido do repo.

Publicar num e esquecer o outro é como os dois ficam diferentes. São dois passos.

A página exclusiva tem endereço diferente em cada um, porque só a Vercel tem
rewrite:

| | Vercel | GitHub Pages |
|---|---|---|
| landing | `/` | `/alertas-tech/` |
| Imperdíveis ML | `/imperdiveis` | `/alertas-tech/imperdiveis.html` |

## O que quebrou em 09/09/2026 (e por que existe a trava)

Três coisas medidas no ar naquele dia:

1. A chave anônima do Supabase estava publicada como `__SUPABASE_ANON_KEY__`, e
   o código só fazia o POST **se** ela fosse diferente disso. Resultado: o
   cadastro era pulado, a página redirecionava como se tivesse dado certo e a
   tabela `leads` tinha **zero linhas** desde sempre.
2. Nenhum dos links de grupo apontava para um grupo onde o motor publica hoje —
   convite de WhatsApp muda quando alguém revoga, e a página não tinha como
   saber.
3. A landing tinha 10 categorias; o motor publica em 18.

Por isso a página agora tem `grupos.json` como fonte única, um script que busca
o convite atual de cada grupo e testes que quebram quando os dois desencontram.

## Fonte da verdade: `grupos.json`

Uma entrada por grupo com `slug`, `nome`, `emoji`, `exemplos`, o **JID** do
grupo de WhatsApp, o **UUID da sessão** dona do grupo no gateway e o canal de
Telegram (`null` quando não existe canal — aí a landing esconde o botão do
Telegram em vez de oferecer um caminho que não leva a lugar nenhum).

São 20 entradas: as **19 categorias** do motor (`monitor/config.py`, mapa
`CANAIS`, do repo `trading_c_agente`) mais **`geral`**, que é o grupo de super
desconto (`GRUPOS_SUPER_DESCONTO` no `.env` do motor). Esse recebe por número e
não por assunto — qualquer produto de qualquer loja acima do piso de desconto —
e é o destino de quem não quer escolher categoria. Ele passa exatamente pelo
mesmo fluxo das outras: caminho especial foi o que já trouxe a falha silenciosa
de volta uma vez.

Os links de convite **não** se escrevem aqui nem à mão: eles vivem no bloco
entre `// GRUPOS:INICIO` e `// GRUPOS:FIM` do `landing.js`, que é reescrito pelo
sincronizador. É um bloco só para todas as páginas — duas cópias do mapa de
grupos seria uma delas com convite morto.

## Sincronizar os links

```bash
export OPENWA_API_KEY=...            # chave do gateway OpenWA (X-API-Key)
python scripts/sincronizar_landing.py --dry-run   # mostra o que mudaria
python scripts/sincronizar_landing.py             # grava no landing.js
```

O alvo padrão é o `landing.js` (`--alvo` troca). Era o `index.html` até
18/09/2026, quando o JS saiu de dentro da página.

Variáveis de ambiente:

| Nome | Para quê | Obrigatória |
|---|---|---|
| `OPENWA_API_KEY` | header `X-API-Key` do gateway OpenWA | sim |
| `OPENWA_BASE_URL` | troca o endereço do gateway (padrão vem do `grupos.json`) | não |

**A chave nunca entra no repositório.** Sem ela o script sai com código 2 e não
toca em nada.

Duas regras do script, as duas nascidas de dor:

- **Se qualquer categoria falhar, nada é escrito.** Link vazio é pior que link
  velho: quem cai num convite morto some sem reclamar. A gravação também é
  atômica (temporário + `os.replace`), para que uma interrupção no meio não
  deixe o arquivo truncado no ar.
- **Pausa entre as consultas.** Medido em 09/09/2026: 18 pedidos de convite em
  sequência começam a voltar HTTP 500 a partir do 12º (o WhatsApp limita), e os
  mesmos grupos respondem 200 quando consultados devagar. O padrão é 2s de
  pausa e 3 tentativas (`--pausa`, `--tentativas`).
  Com 20 grupos (10/09/2026) os 2s de padrão ficaram no limite: a rodada que
  entregou `salao` foi feita com `--pausa 4`, e as 20 responderam 200 na
  primeira tentativa. Categoria nova alonga a fila — suba a pausa junto.

## Testes

```bash
python -m pytest                                    # tudo
python -m coverage run --source=scripts -m pytest   # com cobertura
python -m coverage report -m
```

Neste notebook o interpretador é
`C:\Users\EmanuelleMiranda\.claude\ai-tools\Scripts\python.exe` — o `python` do
PATH é o stub da Microsoft Store.

São quatro frentes, todas **sem rede**:

- `tests/test_landing.py` — a landing bate com o `grupos.json`: toda categoria
  tem card e link, nenhum convite repetido, o placeholder da chave não voltou, a
  chave publicada é mesmo a `anon` do projeto certo, o bloco de consentimento
  existe.
- `tests/test_paginas.py` — o que vale para **toda** página publicada: incluir
  o compartilhado em vez de copiar, por caminho relativo; ter todos os
  elementos que o `landing.js` procura (id que falta é `null.checked`, e o
  cadastro inteiro morre calado); levar a uma política de privacidade que
  existe de verdade; e as rotas do `vercel.json` (regra específica sempre
  antes do catch-all, compartilhado sem cache).
- `tests/test_sincronizar_landing.py` — o script, com o gateway em dublê.
- `tests/test_landing_comportamento.py` — o `landing.js` rodando de verdade no
  `node` contra um DOM de mentira: falha de cadastro aparece na tela, o convite
  é entregue mesmo assim, sem consentimento nada é enviado, e a página sem
  seção de lojas grava a loja fixa (com o DOM se recusando a inventar as caixas
  que ela não tem). Se não houver `node` no PATH, estes testes são **pulados**
  (não silenciosamente aprovados).

## Cadastro (Supabase)

`POST /rest/v1/leads` com a chave `anon` — que é pública por desenho: ela vai no
HTML de qualquer jeito. A policy do banco deixa **inserir** e não deixa **ler**.

Colunas: `nome`, `email`, `telefone`, `categoria`, `plataforma`, `lojas`,
`consentimento`, `consentimento_em`, `origem`, `meio`, `campanha`, `criado_em`.
Atenção: `plataforma` tem CHECK e só aceita `'wpp'` ou `'tg'` — qualquer outro
valor devolve HTTP 400 e o lead se perde. Mandar coluna que não existe dá o
mesmo 400, por isso o espelho do schema está em `tests/test_landing.py`
(`COLUNAS_DE_LEADS`).

### Prova do consentimento

`consentimento_em` guarda **o instante em que a caixa foi marcada**, não o do
envio. É a prova que a LGPD pede como base legal (art. 7º, I) e é também o que
sustenta o link de afiliado: a política de Associados da Amazon só admite esse
tipo de comunicação "desde que tais comunicações sejam solicitadas".

### Origem da visita (para medir campanha)

Campanha sem medir origem não é campanha, é gasto. Todo lead sai com
`origem`/`meio`/`campanha`, nesta ordem de preferência:

1. `?utm_source=`, `utm_medium=`, `utm_campaign=` da URL;
2. o que ficou no `sessionStorage` da primeira visita (recarregar sem UTM não
   apaga a origem real — mas um clique NOVO de campanha vence o guardado);
3. o domínio de `document.referrer` (ex.: `instagram.com`) com `meio: 'referrer'`;
4. `origem: 'direto'`.

O texto do UTM vem da URL, ou seja, do mundo, e vai para o banco: passa por
`UTM_ACEITO` (só caracteres inocentes; o que não bate é descartado, não
"consertado") e é cortado em `UTM_MAX` = 120. A limpeza vale também na leitura
do `sessionStorage`, que é do visitante e dá para editar à mão. Se qualquer
parte disso falhar — Safari privado bloqueando storage, por exemplo — o
cadastro segue e a origem vira `'direto'`: telemetria nunca custa um lead.

## Contagem de visita (o denominador)

Até 22/09/2026 o projeto contava **cadastro** e não contava **visita**: o
numerador sem o denominador. Sem saber quanta gente entra na página não existe
taxa de conversão visita→cadastro, e sem taxa nenhuma mudança na landing pode
ser provada boa ou ruim — foi por isso que um redesenho inteiro foi vetado.

`POST /rest/v1/visitas`, mesma chave `anon`, mesma policy: **inserir sim, ler
não**. Colunas: `pagina`, `hospedagem`, `origem`, `meio`, `campanha` e o
`criado_em` do banco. **Nenhum dado pessoal** — não há pessoa identificada
aqui, e por isso não há consentimento a pedir.

Ficou no Supabase, e não no Analytics do Vercel, porque a mesma página é
servida por **duas** hospedagens (Vercel e o espelho do GitHub Pages) e as duas
recebem gente de verdade: uma medida que só vê o Vercel fica cega para metade
da casa. No mesmo banco, numerador e denominador têm os mesmos campos de
origem, e a taxa por campanha é uma consulta em vez de duas telas.

- **Antes de funcionar, a migration tem de ser aplicada uma vez**:
  `docs/visitas.sql` no SQL Editor do Supabase. Sem isso o POST devolve 404, a
  visita simplesmente não é contada e o cadastro segue igual.
- **Cada página declara o próprio nome** em `<body data-pagina="...">`. Deduzir
  do caminho não serve: o Vercel serve `/imperdiveis` e o GitHub Pages serve
  `/alertas-tech/imperdiveis.html` — o mesmo arquivo viraria duas linhas no
  relatório. Quem esquecer de declarar aparece como `nao-declarada`.
- **Uma visita por página por sessão**: F5 não conta de novo (`sessionStorage`).
  Se o POST não passou, a marca não é gravada — o próximo carregamento tenta
  outra vez em vez de dar a contagem por feita.
- **Dispara e segue**, sem `await`: contagem de visita é telemetria, igual ao
  Pixel. Não segura a página e não pode custar um cadastro.

A taxa, quando a tabela tiver dados. Atenção: `leads` **não** tem coluna
`pagina` — o que as duas tabelas têm em comum é `origem`/`meio`/`campanha`, e é
por aí que a conversão se quebra sem inventar número:

```sql
-- conversão por origem (7 dias)
with v as (select origem, count(*) n from visitas
            where criado_em >= now() - interval '7 days' group by origem),
     l as (select origem, count(*) n from leads
            where criado_em >= now() - interval '7 days' group by origem)
select coalesce(v.origem, l.origem) as origem,
       coalesce(v.n, 0)             as visitas,
       coalesce(l.n, 0)             as cadastros,
       round(100.0 * coalesce(l.n, 0) / nullif(v.n, 0), 1) as taxa_pct
  from v full join l on l.origem = v.origem
 order by visitas desc nulls last;

-- visitas por página e por hospedagem (onde a gente realmente está)
select pagina, hospedagem, count(*) visitas
  from visitas
 where criado_em >= now() - interval '7 days'
 group by pagina, hospedagem
 order by visitas desc;
```

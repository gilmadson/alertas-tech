# AlertasTech — landing

Página única e estática (`index.html`, sem framework e sem build) que capta
quem quer entrar nos grupos de oferta do AlertasTech.

Ela está publicada em **dois** lugares:

- <https://alertastech-landing.vercel.app> — projeto Vercel `alertastech-landing`,
  **não ligado ao GitHub**: o deploy é manual.
- <https://gilmadson.github.io/alertas-tech/> — GitHub Pages, servido do repo.

Publicar num e esquecer o outro é como os dois ficam diferentes. São dois passos.

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

São 19 entradas: as **18 categorias** do motor (`monitor/config.py`, mapa
`CANAIS`, do repo `trading_c_agente`) mais **`geral`**, que é o grupo de super
desconto (`GRUPOS_SUPER_DESCONTO` no `.env` do motor). Esse recebe por número e
não por assunto — qualquer produto de qualquer loja acima do piso de desconto —
e é o destino de quem não quer escolher categoria. Ele passa exatamente pelo
mesmo fluxo das outras: caminho especial foi o que já trouxe a falha silenciosa
de volta uma vez.

Os links de convite **não** se escrevem aqui nem à mão no HTML: eles vivem no
bloco entre `// GRUPOS:INICIO` e `// GRUPOS:FIM` do `index.html`, que é
reescrito pelo sincronizador.

## Sincronizar os links

```bash
export OPENWA_API_KEY=...            # chave do gateway OpenWA (X-API-Key)
python scripts/sincronizar_landing.py --dry-run   # mostra o que mudaria
python scripts/sincronizar_landing.py             # grava no index.html
```

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
  deixe o `index.html` truncado no ar.
- **Pausa entre as consultas.** Medido em 09/09/2026: 18 pedidos de convite em
  sequência começam a voltar HTTP 500 a partir do 12º (o WhatsApp limita), e os
  mesmos grupos respondem 200 quando consultados devagar. O padrão é 2s de
  pausa e 3 tentativas (`--pausa`, `--tentativas`).

## Testes

```bash
python -m pytest                                    # tudo
python -m coverage run --source=scripts -m pytest   # com cobertura
python -m coverage report -m
```

Neste notebook o interpretador é
`C:\Users\EmanuelleMiranda\.claude\ai-tools\Scripts\python.exe` — o `python` do
PATH é o stub da Microsoft Store.

São três frentes, todas **sem rede**:

- `tests/test_landing.py` — a landing bate com o `grupos.json`: toda categoria
  tem card e link, nenhum convite repetido, o placeholder da chave não voltou, a
  chave publicada é mesmo a `anon` do projeto certo, o bloco de consentimento
  existe.
- `tests/test_sincronizar_landing.py` — o script, com o gateway em dublê.
- `tests/test_landing_comportamento.py` — o JS do `index.html` rodando de
  verdade no `node` contra um DOM de mentira: falha de cadastro aparece na tela,
  o convite é entregue mesmo assim, sem consentimento nada é enviado. Se não
  houver `node` no PATH, estes testes são **pulados** (não silenciosamente
  aprovados).

## Cadastro (Supabase)

`POST /rest/v1/leads` com a chave `anon` — que é pública por desenho: ela vai no
HTML de qualquer jeito. A policy do banco deixa **inserir** e não deixa **ler**.

Colunas: `nome`, `email`, `telefone`, `categoria`, `plataforma`, `lojas`,
`criado_em`. Atenção: `plataforma` tem CHECK e só aceita `'wpp'` ou `'tg'` —
qualquer outro valor devolve HTTP 400 e o lead se perde.

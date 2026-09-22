// Dublê de navegador: o mínimo de DOM que a landing usa.
// Serve para rodar o JS do index.html de verdade, sem browser — é assim que a
// prova de "a falha aparece" deixa de ser afirmação e vira execução.

const elementos = {};
const valores = {
  'loja-ml': 'mercadolivre', 'loja-amz': 'amazon', 'loja-mag': 'magalu',
  'loja-shp': 'shopee', 'loja-ali': 'aliexpress', 'loja-kbm': 'kabum',
};

// As páginas exclusivas (Imperdíveis ML) não têm seção de lojas. Com
// DOM_SEM_LOJAS o dublê se recusa a inventar essas caixas: encostar nelas
// quebra o cenário, como quebraria no navegador de verdade.
const semLojas = !!process.env.DOM_SEM_LOJAS;

function elemento(id) {
  if (semLojas && id.startsWith('loja-')) {
    throw new Error('esta página não tem a caixa ' + id);
  }
  if (!elementos[id]) {
    const classes = new Set();
    elementos[id] = {
      id,
      value: valores[id] || '',
      checked: false,
      disabled: false,
      textContent: '',
      innerHTML: '',
      style: {},
      dataset: {},
      classList: {
        add: (c) => classes.add(c),
        remove: (c) => classes.delete(c),
        contains: (c) => classes.has(c),
        toArray: () => [...classes],
      },
      focus() {},
    };
  }
  return elementos[id];
}

let relogio = 1_764_000_000_000;   // instante fixo: data previsível nos testes
export function avancarRelogio(ms) { relogio += ms; }

// O `new Date()` do código de produção precisa andar com o relógio de mentira,
// senão não há como provar que o consentimento guarda o instante do ACEITE e
// não o do envio.
const DataReal = globalThis.Date;
globalThis.Date = class extends DataReal {
  constructor(...args) { super(...(args.length ? args : [relogio])); }
  static now() { return relogio; }
};

// ── mundo de fora, configurado por variável de ambiente ──────────────────────
const amb = process.env;

// O sorteio entre "sem escolha" (Ofertas gerais / Imperdíveis ML) usa
// `Math.random()`. Sob dado de verdade um teste não prova nada — cada lado do
// sorteio precisa de um cenário que force ESSE lado e afirme com certeza.
// `SORTEIO_FORCA_IMPERDIVEIS=1` empurra o dado pra >= 0.5 (cai em
// 'imperdiveis'); qualquer outro valor cai em 'geral' (< 0.5) — mesmo default
// do código de produção (`Math.random() < 0.5 ? 'geral' : 'imperdiveis'`).
globalThis.Math.random = () => (amb.SORTEIO_FORCA_IMPERDIVEIS === '1' ? 0.9 : 0.1);
// A mesma página é servida por DUAS hospedagens (Vercel e GitHub Pages), e as
// duas recebem gente de verdade. Trocar o host aqui é como se prova que a
// medição vê as duas, em vez de metade da casa.
export const HOST = amb.HOSTNAME || 'alertastech-landing.vercel.app';
// Mesma chave que o index.html usa: se la mudar de nome, os testes de sessao
// caem -- que e o aviso certo.
const CHAVE_ORIGEM_TESTE = 'alertastech:origem';
// Idem para a marca de visita já contada: a chave é por página.
const CHAVE_VISITA_TESTE = 'alertastech:visita:';

// Bloqueada é bloqueada: o `hostname` cai junto com o `search`, senão a
// contagem de visita pareceria coberta num caminho que no navegador estoura.
globalThis.location = amb.LOCATION_QUEBRADA
  ? {
      get search() { throw new Error('location bloqueada'); },
      get hostname() { throw new Error('location bloqueada'); },
    }
  : { search: amb.URL_BUSCA || '', hostname: HOST };

const naSessao = {};
if (amb.SESSION_GUARDADO) naSessao[CHAVE_ORIGEM_TESTE] = amb.SESSION_GUARDADO;
// `VISITA_CONTADA_EM=index` = alguém já foi contado NAQUELA página nesta sessão.
if (amb.VISITA_CONTADA_EM) naSessao[CHAVE_VISITA_TESTE + amb.VISITA_CONTADA_EM] = '1';
globalThis.sessionStorage = amb.SESSION_QUEBRADO
  ? {
      getItem() { throw new Error('storage bloqueado'); },
      setItem() { throw new Error('storage bloqueado'); },
    }
  : {
      getItem: (k) => (k in naSessao ? naSessao[k] : null),
      setItem: (k, v) => { naSessao[k] = String(v); },
    };

export const abertas = [];
export const chamadasFetch = [];
export let janelaLiberada = true;
export function bloquearJanela() { janelaLiberada = false; }

// Prova de ORDEM, não só de resultado: o bug de 22/09/2026 não era "a aba não
// abre", era "abre tarde demais". iOS Safari só permite `window.open` dentro
// do mesmo gesto síncrono do toque — uma chamada depois de um `await` (o POST
// no Supabase, por exemplo) é barrada em silêncio, sem erro para capturar.
// `abertas`/`janelaLiberada` provam o QUE aconteceu; isto prova QUANDO.
export const ordemDeChamadas = [];

// Por variável de ambiente porque a contagem de visita sai no CARREGAMENTO,
// antes de o roteiro do cenário rodar: um `responderSupabase()` lá embaixo
// chegaria tarde para ela.
export let respostaDoSupabase = amb.RESPOSTA_STATUS
  ? { ok: false, status: Number(amb.RESPOSTA_STATUS) }
  : { ok: true, status: 201 };
export function responderSupabase(resp) { respostaDoSupabase = resp; }

globalThis.document = {
  getElementById: elemento,
  // `data-lojas` no <body> é como a página exclusiva declara a loja fixa dela.
  // Vazio = página com seção de lojas (o index.html).
  // `data-pagina` é como a página declara o próprio nome para a contagem de
  // visita. Vazio de propósito: o dublê não inventa declaração que a página
  // não fez — é assim que o teste vê o esquecimento.
  body: {
    style: {},
    dataset: { lojas: amb.BODY_LOJAS || '', pagina: amb.BODY_PAGINA || '' },
  },
  referrer: amb.REFERRER || '',
};
globalThis.window = {
  open: (url) => {
    ordemDeChamadas.push('abrir-janela');
    if (!janelaLiberada) return null;
    // Janela de verdade: abrir não é apontar. `abertas` só recebe o destino
    // quando alguém navega ESTA janela para lá — igual ao navegador de
    // verdade, onde `window.open('', '_blank')` e um `janela.location = url`
    // depois são dois atos separados, e só o primeiro precisa do gesto.
    return { set location(destino) { abertas.push(destino); } };
  },
};
globalThis.setTimeout = () => {};   // o focus() atrasado do modal
globalThis.fetch = async (url, opcoes) => {
  ordemDeChamadas.push('fetch:' + (String(url).includes('/leads') ? 'leads' : 'visitas'));
  chamadasFetch.push({ url, opcoes });
  if (respostaDoSupabase instanceof Error) throw respostaDoSupabase;
  return respostaDoSupabase;
};

export function el(id) { return elemento(id); }

// A contagem de visita sai no carregamento de toda página, antes de qualquer
// cadastro. Ela fica em `visitas`, separada: as provas do LEAD contam POST de
// lead, e se a telemetria entrar nessa conta elas passam a medir outra coisa.
const ehVisita = (c) => String(c.url).includes('/rest/v1/visitas');

export function estado() {
  const doLead = chamadasFetch.filter((c) => !ehVisita(c));
  const daVisita = chamadasFetch.filter(ehVisita);
  return {
    aviso: el('form-aviso').innerHTML,
    avisoVisivel: el('form-aviso').classList.contains('ativo'),
    erro: el('form-erro').textContent,
    modalAtivo: el('modal').classList.contains('active'),
    // '' quando ninguém mexeu — que é o estado certo: esconder o formulário
    // esconde junto o #form-aviso, que é filho dele.
    formDisplay: el('lead-form').style.display ?? '',
    notaTelegram: el('tg-nota').textContent,
    consentTexto: el('consent-cat').textContent,
    consentMarcado: el('consent-check').checked,
    botaoTelegram: el('btn-telegram').style.display,
    secaoLojas: el('lojas-section').style.display,
    subtituloModal: el('modal-subtitle').textContent,
    fetchesTentados: doLead.length,
    origemGuardada: naSessao[CHAVE_ORIGEM_TESTE] ?? null,
    abertas,
    ordemDeChamadas,
    fetches: doLead.map((c) => ({
      url: c.url,
      corpo: JSON.parse(c.opcoes.body),
      apikey: (c.opcoes.headers.apikey || '').slice(0, 12),
    })),
    visitas: daVisita.map((c) => ({
      url: c.url,
      corpo: JSON.parse(c.opcoes.body),
      apikey: (c.opcoes.headers.apikey || '').slice(0, 12),
    })),
  };
}

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
export const HOST = 'alertastech-landing.vercel.app';
// Mesma chave que o index.html usa: se la mudar de nome, os testes de sessao
// caem -- que e o aviso certo.
const CHAVE_ORIGEM_TESTE = 'alertastech:origem';

globalThis.location = amb.LOCATION_QUEBRADA
  ? { get search() { throw new Error('location bloqueada'); }, hostname: HOST }
  : { search: amb.URL_BUSCA || '', hostname: HOST };

const naSessao = {};
if (amb.SESSION_GUARDADO) naSessao[CHAVE_ORIGEM_TESTE] = amb.SESSION_GUARDADO;
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

export let respostaDoSupabase = { ok: true, status: 201 };
export function responderSupabase(resp) { respostaDoSupabase = resp; }

globalThis.document = {
  getElementById: elemento,
  // `data-lojas` no <body> é como a página exclusiva declara a loja fixa dela.
  // Vazio = página com seção de lojas (o index.html).
  body: { style: {}, dataset: { lojas: amb.BODY_LOJAS || '' } },
  referrer: amb.REFERRER || '',
};
globalThis.window = {
  open: (url) => { abertas.push(url); return janelaLiberada ? {} : null; },
};
globalThis.setTimeout = () => {};   // o focus() atrasado do modal
globalThis.fetch = async (url, opcoes) => {
  chamadasFetch.push({ url, opcoes });
  if (respostaDoSupabase instanceof Error) throw respostaDoSupabase;
  return respostaDoSupabase;
};

export function el(id) { return elemento(id); }

export function estado() {
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
    fetchesTentados: chamadasFetch.length,
    origemGuardada: naSessao[CHAVE_ORIGEM_TESTE] ?? null,
    abertas,
    fetches: chamadasFetch.map((c) => ({
      url: c.url,
      corpo: JSON.parse(c.opcoes.body),
      apikey: (c.opcoes.headers.apikey || '').slice(0, 12),
    })),
  };
}

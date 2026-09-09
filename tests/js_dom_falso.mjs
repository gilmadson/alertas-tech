// Dublê de navegador: o mínimo de DOM que a landing usa.
// Serve para rodar o JS do index.html de verdade, sem browser — é assim que a
// prova de "a falha aparece" deixa de ser afirmação e vira execução.

const elementos = {};
const valores = {
  'loja-ml': 'mercadolivre', 'loja-amz': 'amazon', 'loja-mag': 'magalu',
  'loja-shp': 'shopee', 'loja-ali': 'aliexpress', 'loja-kbm': 'kabum',
};

function elemento(id) {
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

let relogio = 1_000_000;
export function avancarRelogio(ms) { relogio += ms; }

export const abertas = [];
export const chamadasFetch = [];
export let janelaLiberada = true;
export function bloquearJanela() { janelaLiberada = false; }

export let respostaDoSupabase = { ok: true, status: 201 };
export function responderSupabase(resp) { respostaDoSupabase = resp; }

globalThis.document = { getElementById: elemento, body: { style: {} } };
globalThis.window = {
  open: (url) => { abertas.push(url); return janelaLiberada ? {} : null; },
};
globalThis.Date.now = () => relogio;
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
    abertas,
    fetches: chamadasFetch.map((c) => ({
      url: c.url,
      corpo: JSON.parse(c.opcoes.body),
      apikey: (c.opcoes.headers.apikey || '').slice(0, 12),
    })),
  };
}

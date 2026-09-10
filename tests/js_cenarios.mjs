// Roteiro dos cenários. Roda o JS de verdade do index.html contra o dublê de
// DOM e imprime o estado final em JSON, que o pytest confere.

const cenario = process.env.CENARIO;

function preencher({ consent = true, captcha = true, tel = '81999998888' } = {}) {
  el('lead-tel').value = tel;
  el('captcha-check').checked = captcha;
  el('consent-check').checked = consent;
  // É o onchange da caixa: registra o instante do aceite e revalida o formulário.
  marcarConsentimento();
}

async function submeter(plat) {
  const botao = { dataset: { plat }, disabled: false, textContent: '' };
  await submeterLead({ preventDefault() {}, submitter: botao });
  return botao;
}

const extra = {};

if (cenario === 'cadastro') {
  // Cenário genérico da telemetria: o que muda é o ambiente (URL_BUSCA,
  // REFERRER, SESSION_GUARDADO, SESSION_QUEBRADO, LOCATION_QUEBRADA), não o
  // roteiro. O aceite acontece 5s antes do envio, de propósito.
  abrirModal('📱', 'Smartphones', 'smartphone');
  preencher();
  extra.instanteDoAceite = new Date().toISOString();
  avancarRelogio(5000);
  await submeter('wpp');
  extra.instanteDoEnvio = new Date().toISOString();

} else if (cenario === 'sucesso') {
  abrirModal('📱', 'Smartphones', 'smartphone');
  avancarRelogio(5000);
  preencher();
  extra.botaoLiberado = !el('btn-whatsapp').disabled;
  await submeter('wpp');

} else if (cenario === 'falha_http') {
  responderSupabase({ ok: false, status: 500 });
  abrirModal('📱', 'Smartphones', 'smartphone');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'falha_rede') {
  responderSupabase(new Error('offline'));
  abrirModal('📱', 'Smartphones', 'smartphone');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'sem_consentimento') {
  abrirModal('📱', 'Smartphones', 'smartphone');
  avancarRelogio(5000);
  preencher({ consent: false });
  extra.botaoLiberado = !el('btn-whatsapp').disabled;
  await submeter('wpp');

} else if (cenario === 'popup_bloqueado') {
  bloquearJanela();
  abrirModal('📱', 'Smartphones', 'smartphone');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'geral') {
  abrirModal('🔥', 'Ofertas gerais', 'geral');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'geral_falha_http') {
  responderSupabase({ ok: false, status: 500 });
  abrirModal('🔥', 'Ofertas gerais', 'geral');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'envio_rapido') {
  // Sem avancarRelogio: é o envio em menos de 1,5s. Autofill do telefone e
  // dois toques cabem nisso num aparelho rápido.
  abrirModal('📱', 'Smartphones', 'smartphone');
  preencher();
  await submeter('wpp');

} else if (cenario === 'telegram_categoria_nova') {
  abrirModal('👜', 'Moda & Acessórios', 'moda');
  avancarRelogio(5000);
  preencher();
  await submeter('tg');

} else {
  throw new Error('cenário desconhecido: ' + cenario);
}

console.log(JSON.stringify({ ...estado(), ...extra }));

// Roteiro dos cenários. Roda o JS de verdade do index.html contra o dublê de
// DOM e imprime o estado final em JSON, que o pytest confere.

const cenario = process.env.CENARIO;

function preencher({ consent = true, tel = '81999998888' } = {}) {
  el('lead-tel').value = tel;
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

} else if (cenario === 'geral_sorteado_imperdiveis') {
  // Mesmo clique de sempre em "Ofertas gerais" (card e nome não mudam) — só o
  // dado (forçado por SORTEIO_FORCA_IMPERDIVEIS) cai do outro lado.
  abrirModal('🔥', 'Ofertas gerais', 'geral');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'imperdiveis_direto_no_grid') {
  // "Imperdíveis ML" clicado na página com TODAS as categorias (não a
  // exclusiva) — antes pedia loja igual qualquer card comum; devia ser fixo
  // em Mercado Livre desde sempre, já que o grupo só manda ML mesmo aqui.
  abrirModal('⚡', 'Imperdíveis ML', 'imperdiveis');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'envio_rapido') {
  // Sem avancarRelogio: é o envio em menos de 1,5s. Autofill do telefone e
  // dois toques cabem nisso num aparelho rápido.
  abrirModal('📱', 'Smartphones', 'smartphone');
  preencher();
  await submeter('wpp');

} else if (cenario === 'salao') {
  // Card comum do grid com `tg: null`: o botão do Telegram tem de sumir sem
  // que nada mais mude — o `geral` já provava isso, mas ele é o card em
  // destaque e por muito tempo teve caminho próprio.
  abrirModal('💇', 'Salão de Beleza', 'salao');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'imperdiveis') {
  // Página exclusiva: sem grade e sem seção de lojas. Roda com o dublê
  // estrito (DOM_SEM_LOJAS), então qualquer toque numa caixa `loja-*` mata o
  // cenário — que é o ponto.
  abrirModal('⚡', 'Imperdíveis ML', 'imperdiveis');
  avancarRelogio(5000);
  preencher();
  extra.botaoLiberado = !el('btn-whatsapp').disabled;
  await submeter('wpp');

} else if (cenario === 'imperdiveis_falha_http') {
  responderSupabase({ ok: false, status: 500 });
  abrirModal('⚡', 'Imperdíveis ML', 'imperdiveis');
  avancarRelogio(5000);
  preencher();
  await submeter('wpp');

} else if (cenario === 'abertura_automatica') {
  // Ninguém chama abrirModal aqui: é o próprio landing.js que clica sozinho
  // no card, no carregamento, quando `data-auto-abrir` está no body (env
  // BODY_AUTOABRIR). Os cenários de página exclusiva acima chamam abrirModal
  // direto — nenhum deles prova que o clique automático em si funciona.
  extra.modalAtivoSozinho = el('modal').classList.contains('active');

} else if (cenario === 'cancelar_em_pagina_sem_grade') {
  // "Cancelar" numa página sem grade não pode deixar tela vazia (achado do
  // projeto-arquiteto, 23/09/2026): sem card pra clicar de novo, só o F5
  // resolvia antes. O carregamento já abriu o modal sozinho (BODY_AUTOABRIR);
  // preenche, cancela, e confere que reabriu limpo em vez de sumir.
  avancarRelogio(5000);
  preencher();
  el('lead-nome').value = 'Fulano';
  fecharModal();

} else if (cenario === 'cancelar_em_pagina_com_grade') {
  // Sem BODY_AUTOABRIR: página comum continua com o comportamento de sempre
  // — cancelar fecha o modal, a grade por baixo resolve.
  abrirModal('📱', 'Smartphones', 'smartphone');
  avancarRelogio(5000);
  preencher();
  fecharModal();

} else if (cenario === 'visita') {
  // Só o carregamento, ninguém toca em nada: a contagem de visita tem de sair
  // sozinha. É o caso de quem entra e vai embora — exatamente quem nunca
  // aparece na tabela de leads, e por isso faltava no denominador.
  await Promise.resolve();
  await Promise.resolve();

} else if (cenario === 'visita_recarregada') {
  // A visita do carregamento já saiu lá em cima. Espera ela assentar e chama
  // de novo: é o F5 na mesma sessão.
  await Promise.resolve();
  await Promise.resolve();
  await registrarVisita();

} else if (cenario === 'pagina_sem_grade_nao_trava_a_tela') {
  // Bug de 23/09/2026 (ele, no Safari e no navegador do Telegram): a página
  // de Smartphone abria "congelada", sem os campos. O abrirModal travava a
  // rolagem do body e agendava o foco no telefone — herança do modal por
  // cima da grade. Em página sem grade o formulário É a página: travar a
  // rolagem prende a pessoa no topo, e o foco automático rola a tela sozinho.
  // O carregamento já abriu o formulário (BODY_AUTOABRIR); só lê o estado.
  extra.overflowDoBody = document.body.style.overflow || '';
  extra.timersAgendados = globalThis.timersAgendados;

} else if (cenario === 'modal_por_cima_da_grade_ainda_trava') {
  abrirModal('📱', 'Smartphones', 'smartphone');
  extra.overflowDoBody = document.body.style.overflow || '';
  extra.timersAgendados = globalThis.timersAgendados;

} else if (cenario === 'toque_na_margem_da_pagina_sem_grade') {
  // Sem popup, o toque na margem em volta do formulário (o próprio #modal)
  // não pode reabrir o formulário e apagar o que a pessoa digitou.
  preencher();
  fecharModal({ target: el('modal') });
  extra.telDepois = el('lead-tel').value;

} else if (cenario === 'telegram_categoria_nova') {
  abrirModal('👜', 'Moda & Acessórios', 'moda');
  avancarRelogio(5000);
  preencher();
  await submeter('tg');

} else {
  throw new Error('cenário desconhecido: ' + cenario);
}

console.log(JSON.stringify({ ...estado(), ...extra }));

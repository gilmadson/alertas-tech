-- Coluna `conteudo`: qual POST trouxe a pessoa.
--
-- Desde 09/09/2026 todo lead sai com `origem`/`meio`/`campanha`, e desde
-- 22/09/2026 toda visita também. Esses três dizem de qual CAMPANHA a pessoa
-- veio — e nenhum deles diz de qual PUBLICAÇÃO. Dois criativos rodando na
-- mesma campanha caem no mesmo balde: aparece um número só, e não há como ver
-- qual post traz gente e qual só faz volume.
--
-- O valor é o `utm_content` da URL (`?utm_source=...&utm_content=reel-03`),
-- limpo pela MESMA regra dos outros UTM na landing: lista de caracteres
-- aceitos e teto de 120. Quem chega sem `utm_content` grava null, exatamente
-- como antes — nada no cadastro muda por causa disto.
--
-- Aqui fica só o DADO BRUTO. Não existe cálculo de "eficiência" no banco nem
-- no código: quem lê os números e decide o que presta é o Gilmadson.
--
-- Nas DUAS tabelas de propósito: `conteudo` só na `leads` daria cadastro por
-- post sem saber quanta gente aquele post trouxe — o numerador sem o
-- denominador de novo.
--
-- Segurança: nada muda. As duas tabelas já têm RLS ligado e já são
-- insert-only pela chave `anon`; esta migration só acrescenta uma coluna de
-- texto, e o texto vem da URL — não é dado pessoal e não identifica ninguém.
--
-- Como aplicar (uma vez, no projeto jfuqmjbxzhoceycauhys):
--   Supabase -> SQL Editor -> cola este arquivo -> Run.
-- Pode ser colado de novo sem medo: `if not exists` nas duas linhas.
-- Enquanto não for aplicado, o POST da landing devolve HTTP 400 na coluna que
-- o banco não tem — ou seja, aplique ANTES de publicar a landing nova.

alter table public.visitas add column if not exists conteudo text;

alter table public.leads   add column if not exists conteudo text;

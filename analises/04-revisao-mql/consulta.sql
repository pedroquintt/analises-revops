-- Estudo 04 · Revisão da definição de MQL
-- Definição revisada: MQL = pessoa (não deal, não sessão) com pelo menos um deal no CRM,
-- datada pelo primeiro toque (o menor entre formulário e CRM).

-- name: funil_mensal
with deals_email as (
    -- deal sem contato no CRM: o e-mail está no nome do deal ("[Pós] Nome - email")
    select *,
           lower(coalesce(email, regexp_extract(nome_deal, '[\w.+-]+@[\w.-]+'))) as email_resolvido
    from deals
),
toques as (
    select lower(email) as email_norm, criado_em as quando, 'formulario' as fonte from sessoes_formulario
    union all
    select email_resolvido, criado_em, 'crm' from deals_email
),
pessoa as (
    select coalesce(i.pessoa_id, t.email_norm) as pessoa,
           min(t.quando) as primeiro_toque,
           bool_or(t.fonte = 'crm') as e_mql
    from toques t
    left join identidade i using (email_norm)
    group by 1
),
ingenuo as (
    -- contagem de quem não resolve o e-mail do nome: deal sem e-mail vira uma pessoa a mais
    select strftime(date_trunc('month', min(criado_em)), '%Y-%m') as mes,
           coalesce(lower(email), deal_id) as chave
    from deals
    group by 2
)
select
    p.mes,
    p.leads_pessoa,
    p.mql_pessoa,
    s.sessoes_formulario,
    d.deals,
    i.mql_ingenuo,
    round(100.0 * p.mql_pessoa / p.leads_pessoa, 1) as pct_lead_vira_mql
from (
    select strftime(date_trunc('month', primeiro_toque), '%Y-%m') as mes,
           count(*) as leads_pessoa,
           count(*) filter (where e_mql) as mql_pessoa
    from pessoa group by 1
) p
join (select strftime(date_trunc('month', criado_em), '%Y-%m') as mes, count(*) as sessoes_formulario
      from sessoes_formulario group by 1) s using (mes)
join (select strftime(date_trunc('month', criado_em), '%Y-%m') as mes, count(*) as deals
      from deals group by 1) d using (mes)
join (select mes, count(*) as mql_ingenuo from ingenuo group by 1) i using (mes)
order by p.mes;

-- name: o_que_vira_mql
-- O bot de qualificação cria deal para toda faixa de renda menos "sem renda".
select
    p.faixa_salarial,
    p.tier,
    count(*) as pessoas,
    count(d.email) as viraram_mql,
    round(100.0 * count(d.email) / count(*), 1) as pct_mql
from pessoas p
left join (select distinct lower(coalesce(email, regexp_extract(nome_deal, '[\w.+-]+@[\w.-]+'))) as email
           from deals) d on d.email = lower(p.email)
group by 1, 2
order by 2, 1;

-- name: destino_do_mql
-- O que acontece com o MQL depois de entrar (primeiro deal de cada pessoa).
with primeiro_deal as (
    select *
    from deals
    qualify row_number() over (
        partition by lower(coalesce(email, regexp_extract(nome_deal, '[\w.+-]+@[\w.-]+')))
        order by criado_em
    ) = 1
)
select
    case
        when pipeline = 'vendas' then '1. agendou call (foi para vendas)'
        when motivo_perda in ('sem experiência', 'dados inválidos', 'renda abaixo do perfil', 'sem interesse')
            then '2. descartado pelo SDR: ' || motivo_perda
        when motivo_perda = 'não respondeu' then '3. sem resposta'
        else '4. em aberto'
    end as destino,
    count(*) as mql,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from primeiro_deal
group by 1
order by 1;

-- name: chave_de_contagem
-- Três jeitos de contar MQL na mesma base: deal, e-mail do contato e pessoa resolvida.
select
    count(*) as por_deal,
    count(distinct coalesce(lower(email), deal_id)) as por_email_do_contato,
    count(distinct lower(coalesce(email, regexp_extract(nome_deal, '[\w.+-]+@[\w.-]+')))) as por_pessoa_resolvida,
    count(*) filter (where email is null) as deals_sem_email_no_contato
from deals;

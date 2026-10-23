-- Estudo 05 · Tiers de lead e previsibilidade de receita
-- Tier vem da faixa de renda declarada no formulário: A (acima de 6k), B (3k-6k), C (até 3k), D (sem renda).

-- name: conversao_por_tier
-- Conversão histórica de lead em venda por tier, medida em jan-fev (leads maduros).
with compra_pessoa as (
    select i.pessoa_id, min(c.data_compra) as data_compra, sum(c.valor) as valor
    from compras c join identidade i on i.email_norm = lower(c.email)
    group by 1
)
select
    p.tier,
    count(*) as leads,
    count(cp.pessoa_id) as vendas,
    round(100.0 * count(cp.pessoa_id) / count(*), 2) as conversao_pct,
    round(avg(cp.valor), 0) as ticket_medio
from pessoas p
left join compra_pessoa cp using (pessoa_id)
where p.primeiro_toque < date '2025-03-01'
group by 1
order by 1;

-- name: mix_mensal
-- Participação de cada tier nos leads do mês.
select
    strftime(date_trunc('month', primeiro_toque), '%Y-%m') as mes,
    count(*) as leads,
    round(100.0 * count(*) filter (where tier = 'A') / count(*), 1) as pct_a,
    round(100.0 * count(*) filter (where tier = 'B') / count(*), 1) as pct_b,
    round(100.0 * count(*) filter (where tier = 'C') / count(*), 1) as pct_c,
    round(100.0 * count(*) filter (where tier = 'D') / count(*), 1) as pct_d
from pessoas
group by 1
order by 1;

-- name: indicador_semanal
-- Por semana: receita que os leads da semana DEVEM gerar (leads × conversão do tier × ticket,
-- calibrado em jan-fev) contra a receita que de fato entrou na semana.
-- O primeiro é conhecido no dia em que o lead chega; o segundo, semanas depois.
with conv as (
    select
        p.tier,
        count(distinct p.pessoa_id) filter (where c.compra_id is not null) * 1.0 / count(distinct p.pessoa_id) as taxa,
        coalesce(avg(c.valor), 0) as ticket
    from pessoas p
    left join identidade i on i.pessoa_id = p.pessoa_id
    left join compras c on lower(c.email) = i.email_norm
    where p.primeiro_toque < date '2025-03-01'
    group by 1
),
esperado as (
    select date_trunc('week', p.primeiro_toque) as semana, count(*) as leads,
           sum(cv.taxa * cv.ticket) as receita_esperada
    from pessoas p join conv cv using (tier)
    group by 1
),
realizado as (
    select date_trunc('week', data_compra) as semana, sum(valor) as receita_realizada
    from compras group by 1
)
select
    strftime(e.semana, '%Y-%m-%d') as semana,
    e.leads,
    round(e.receita_esperada, 0) as receita_esperada_dos_leads,
    round(coalesce(r.receita_realizada, 0), 0) as receita_realizada
from esperado e
left join realizado r using (semana)
where e.semana >= date '2025-01-06' and e.semana < date '2025-06-30'
order by 1;

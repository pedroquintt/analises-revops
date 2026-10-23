-- Estudo 01 · Churn é arrependimento da 1ª semana
-- Coorte maturada: compras até 31/05, para todas terem pelo menos 30 dias de janela de reembolso.

-- name: tempo_ate_reembolso
-- Quanto tempo depois da compra o pedido de reembolso chega.
with base as (
    select date_diff('day', c.data_compra, r.solicitado_em) as dias
    from reembolsos r
    join compras c using (compra_id)
)
select
    case when dias <= 7 then '0-7 dias'
         when dias <= 30 then '8-30 dias'
         else '31+ dias' end as faixa,
    count(*) as reembolsos,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct,
    round(100.0 * sum(count(*)) over (order by min(dias)) / sum(count(*)) over (), 1) as pct_acumulado
from base
group by 1
order by min(dias);

-- name: grao_compra_vs_transacao
-- A mesma taxa calculada em dois grãos. Pix com entrada + saldo e boleto parcelado geram várias
-- transações por compra, então "reembolsos ÷ transações" esconde o problema.
with tx as (
    select compra_id, count(*) as n_transacoes from transacoes group by 1
)
select
    c.forma_pagamento,
    count(*) as compras,
    sum(tx.n_transacoes) as transacoes,
    count(r.compra_id) as reembolsos,
    round(100.0 * count(r.compra_id) / count(*), 1) as taxa_por_compra,
    round(100.0 * count(r.compra_id) / sum(tx.n_transacoes), 1) as taxa_por_transacao
from compras c
join tx using (compra_id)
left join (select distinct compra_id from reembolsos) r using (compra_id)
where c.data_compra < date '2025-06-01'
group by 1
order by 1;

-- name: filtro_conta_churn
-- O indicador "oficial" exclui estorno de 1ª parcela, retido e downsell.
-- E o estorno de 1ª parcela só passou a ser registrado em abril: antes disso ele não existe na base.
with compras_mes as (
    select date_trunc('month', data_compra) as mes, compra_id
    from compras
    where data_compra < date '2025-06-01'
),
r as (
    select compra_id,
           bool_or(tipo not in ('estorno_primeira_parcela', 'retido', 'downsell')) as conta_churn,
           bool_or(tipo = 'estorno_primeira_parcela') as estorno_1a
    from reembolsos
    group by 1
)
select
    strftime(mes, '%Y-%m') as mes,
    count(*) as compras,
    count(r.compra_id) as reembolso_amplo,
    count(*) filter (where r.conta_churn) as reembolso_conta_churn,
    count(*) filter (where r.estorno_1a) as estorno_primeira_parcela,
    round(100.0 * count(r.compra_id) / count(*), 1) as taxa_ampla,
    round(100.0 * count(*) filter (where r.conta_churn) / count(*), 1) as taxa_conta_churn
from compras_mes
left join r using (compra_id)
group by mes
order by mes;

-- name: perfil_da_venda
-- Onde o reembolso se concentra: forma de pagamento × venda decidida na 1ª call × duração da call.
with perfil as (
    select
        c.compra_id,
        case
            when c.forma_pagamento = 'pix' then '1. Pix'
            when cast(c.data_compra as date) > cast(k.inicio_agendado as date) then '2. Parcelado, decidido depois'
            when k.duracao_min < 70 then '3. Parcelado na 1ª call (< 70 min)'
            else '4. Parcelado na 1ª call (≥ 70 min)'
        end as perfil
    from compras c
    join calls k using (agenda_id)
    where c.data_compra < date '2025-06-01'
)
select
    perfil,
    count(*) as compras,
    count(r.compra_id) as reembolsos,
    round(100.0 * count(r.compra_id) / count(*), 1) as taxa_reembolso
from perfil
left join (select distinct compra_id from reembolsos) r using (compra_id)
group by 1
order by 1;

-- name: motivos
select motivo, count(*) as reembolsos, round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from reembolsos
group by 1
order by 2 desc;

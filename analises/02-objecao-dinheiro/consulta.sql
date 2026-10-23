-- Estudo 02 · "% de perda por dinheiro" mede quem registra a perda, não a call

-- name: crm_por_mes
-- Régua do CRM: perdas depois da call que têm motivo preenchido, e quantas dizem "dinheiro".
select
    strftime(date_trunc('month', fechado_em), '%Y-%m') as mes,
    count(*) as perdas_pos_call,
    count(motivo_perda) as com_motivo,
    round(100.0 * count(motivo_perda) / count(*), 1) as pct_preenchido,
    count(*) filter (where motivo_perda = 'dinheiro') as motivo_dinheiro,
    round(100.0 * count(*) filter (where motivo_perda = 'dinheiro') / nullif(count(motivo_perda), 0), 1) as pct_dinheiro_crm
from deals
where closer is not null
  and win = false
  and coalesce(motivo_perda, '') <> 'no-show'
  and fechado_em < date '2025-07-01'
group by 1
order by 1;

-- name: crm_por_closer
-- Quem alimenta o indicador.
select
    closer,
    count(*) as perdas_pos_call,
    count(motivo_perda) as com_motivo,
    round(100.0 * count(motivo_perda) / count(*), 1) as pct_preenchido,
    count(*) filter (where motivo_perda = 'dinheiro') as motivo_dinheiro,
    round(100.0 * count(*) filter (where motivo_perda = 'dinheiro')
          / sum(count(*) filter (where motivo_perda = 'dinheiro')) over (), 1) as pct_do_total_dinheiro
from deals
where closer is not null
  and win = false
  and coalesce(motivo_perda, '') <> 'no-show'
  and fechado_em < date '2025-07-01'
group by 1
order by 1;

-- name: transcricao_por_mes
-- Régua da call: entre as calls realizadas que não viraram venda, em quantas o lead levantou
-- a objeção de dinheiro (flag extraída da transcrição). Conta por call, não depende de registro.
select
    strftime(date_trunc('month', k.inicio_agendado), '%Y-%m') as mes,
    count(*) as calls_sem_venda,
    count(*) filter (where t.objecao_dinheiro) as com_objecao_dinheiro,
    round(100.0 * count(*) filter (where t.objecao_dinheiro) / count(*), 1) as pct_dinheiro_call
from transcricoes_call t
join calls k using (agenda_id)
where not t.virou_venda
group by 1
order by 1;

-- name: conversao_com_objecao
-- Objeção de dinheiro trava a venda, mas não sempre: conversão de quem levantou × quem não levantou.
select
    objecao_dinheiro,
    count(*) as calls_realizadas,
    count(*) filter (where virou_venda) as vendas,
    round(100.0 * count(*) filter (where virou_venda) / count(*), 1) as conversao
from transcricoes_call
group by 1
order by 1;

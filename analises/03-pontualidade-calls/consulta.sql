-- Estudo 03 · Pontualidade das calls: quanto tempo o lead espera o vendedor entrar

-- name: join_sem_janela
-- O erro clássico: casar agenda e log só pelo código da sala. A sala é reutilizada pelo mesmo
-- vendedor, então cada agenda puxa sessões de outros dias e o "atraso" sai impossível.
with casado as (
    select a.agenda_id,
           count(*) as sessoes_casadas,
           min(date_diff('minute', a.inicio_agendado, s.entrada)) as atraso_min_mais_cedo,
           max(date_diff('minute', a.inicio_agendado, s.entrada)) as atraso_min_mais_tarde
    from agendas a
    join sessoes_sala s on s.codigo_sala = a.codigo_sala and s.participante = 'vendedor'
    group by 1
)
select
    count(*) as agendas,
    round(avg(sessoes_casadas), 1) as sessoes_por_agenda,
    min(atraso_min_mais_cedo) as menor_atraso_min,
    max(atraso_min_mais_tarde) as maior_atraso_min,
    round(max(atraso_min_mais_tarde) / 60.0 / 24, 0) as maior_atraso_dias
from casado;

-- name: join_com_janela
-- Com a janela de -30 a +120 minutos (view `calls`): no máximo uma sessão por agenda.
select
    count(*) as agendas,
    count(entrada_vendedor) as com_sessao_do_vendedor,
    count(*) filter (where realizada) as calls_realizadas,
    min(espera_min) as menor_espera_min,
    max(espera_min) as maior_espera_min
from calls;

-- name: distribuicao_espera
select
    case when espera_min = 0 then '0 (pontual)'
         when espera_min <= 2 then '1-2 min'
         when espera_min <= 5 then '3-5 min'
         when espera_min <= 10 then '6-10 min'
         else 'mais de 10 min' end as faixa,
    count(*) as calls,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from calls
where realizada
group by 1
order by min(espera_min);

-- name: linha_de_base_por_closer
-- Linha de base, não ranking: ordem alfabética, sem meta e sem "pior vendedor".
select
    closer,
    count(*) as calls_realizadas,
    median(espera_min) as mediana_min,
    quantile_cont(espera_min, 0.9) as p90_min,
    round(100.0 * count(*) filter (where espera_min > 5) / count(*), 1) as pct_acima_5min,
    round(sum(espera_min) / 60.0, 1) as horas_de_espera
from calls
where realizada
group by 1
order by 1;

-- name: total
select
    count(*) as calls_realizadas,
    round(sum(espera_min) / 60.0, 1) as horas_de_espera_total,
    round(avg(espera_min), 1) as espera_media_min,
    round(100.0 * count(*) filter (where espera_min > 5) / count(*), 1) as pct_acima_5min
from calls
where realizada;

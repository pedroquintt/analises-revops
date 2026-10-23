-- Views de base reutilizadas pelos estudos.

-- Identidade: qualquer e-mail conhecido do contato (principal ou secundário) aponta para a pessoa.
create view identidade as
select lower(trim(email)) as email_norm, pessoa_id, principal
from contato_emails;

-- Calls: agenda × log de sessões da sala.
-- A sala é reutilizada pelo mesmo vendedor em dias diferentes, então o join pelo código da sala
-- precisa de janela de tempo (-30 min a +120 min do horário marcado). Dentro da janela, fica a
-- sessão mais próxima do horário marcado.
create view calls as
with vendedor as (
    select a.agenda_id, s.entrada, s.saida
    from agendas a
    join sessoes_sala s
      on s.codigo_sala = a.codigo_sala
     and s.participante = 'vendedor'
     and s.entrada between a.inicio_agendado - interval 30 minute
                       and a.inicio_agendado + interval 120 minute
    qualify row_number() over (
        partition by a.agenda_id
        order by abs(date_diff('second', a.inicio_agendado, s.entrada))
    ) = 1
),
lead as (
    select a.agenda_id, s.entrada
    from agendas a
    join sessoes_sala s
      on s.codigo_sala = a.codigo_sala
     and s.participante = 'lead'
     and s.entrada between a.inicio_agendado - interval 30 minute
                       and a.inicio_agendado + interval 120 minute
    qualify row_number() over (
        partition by a.agenda_id
        order by abs(date_diff('second', a.inicio_agendado, s.entrada))
    ) = 1
),
juntas as (
    select
        a.agenda_id,
        a.closer,
        a.email_convidado,
        a.inicio_agendado,
        v.entrada as entrada_vendedor,
        l.entrada as entrada_lead,
        date_diff('minute', v.entrada, v.saida) as duracao_min
    from agendas a
    left join vendedor v using (agenda_id)
    left join lead l using (agenda_id)
)
select
    *,
    -- realizada = o lead entrou e o vendedor ficou pelo menos 20 minutos
    coalesce(entrada_lead is not null and duracao_min >= 20, false) as realizada,
    case
        when entrada_lead is not null and duracao_min >= 20
        then greatest(0, date_diff('minute', greatest(inicio_agendado, entrada_lead), entrada_vendedor))
    end as espera_min
from juntas;

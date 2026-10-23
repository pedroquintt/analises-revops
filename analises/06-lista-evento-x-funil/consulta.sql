-- Estudo 06 · Cruzar a lista de inscritos de um evento com agenda e venda
-- Evento em 20/05/2025, 19h. Quatro camadas de identificação, da mais segura para a menos segura;
-- cada inscrito fica com a primeira camada que o identifica.

-- name: _setup
create or replace view casamento as
with base as (
    select
        inscricao_id,
        lower(trim(email)) as email_norm,
        right(regexp_replace(coalesce(telefone, ''), '\D', '', 'g'), 9) as fone9,
        lower(strip_accents(trim(nome))) as nome_norm
    from inscritos_evento
),
pessoa as (
    select pessoa_id, lower(email) as email_principal,
           right(telefone, 9) as fone9,
           lower(strip_accents(nome)) as nome_norm
    from pessoas
),
nome_unico as (
    -- nome só serve se for único na base; homônimo não é match
    select nome_norm, any_value(pessoa_id) as pessoa_id
    from pessoa group by 1 having count(*) = 1
),
camadas as (
    select b.inscricao_id, 1 as camada, p.pessoa_id
    from base b join pessoa p on p.email_principal = b.email_norm
    union all
    select b.inscricao_id, 2, p.pessoa_id
    from base b join pessoa p on b.fone9 <> '' and p.fone9 = b.fone9
    union all
    select b.inscricao_id, 3, i.pessoa_id
    from base b join identidade i on i.email_norm = b.email_norm and not i.principal
    union all
    select b.inscricao_id, 4, n.pessoa_id
    from base b join nome_unico n using (nome_norm)
)
select inscricao_id, camada, pessoa_id
from camadas
qualify row_number() over (partition by inscricao_id order by camada) = 1;

create or replace view desfecho_pessoa as
-- agenda e compra ligadas à pessoa por QUALQUER e-mail do contato
select
    p.pessoa_id,
    bool_or(c.data_compra < timestamp '2025-05-20 19:00') as ja_era_cliente,
    bool_or(a.inicio_agendado >= timestamp '2025-05-20 19:00') as agendou_depois,
    bool_or(c.data_compra >= timestamp '2025-05-20 19:00') as comprou_depois,
    sum(c.valor) filter (where c.data_compra >= timestamp '2025-05-20 19:00') as receita_depois
from pessoas p
left join identidade i on i.pessoa_id = p.pessoa_id
left join agendas a on lower(a.email_convidado) = i.email_norm
left join compras c on lower(c.email) = i.email_norm
group by 1;

-- name: resumo_camadas
-- Quantos inscritos cada camada acrescenta.
select
    case camada when 1 then '1. e-mail principal'
                when 2 then '2. telefone (9 últimos dígitos)'
                when 3 then '3. e-mail secundário do contato'
                when 4 then '4. nome único na base' end as camada,
    count(*) as inscritos,
    sum(count(*)) over (order by camada) as acumulado
from casamento
group by camada
order by camada;

-- name: homonimos
-- Por que nome sozinho é a última camada: quantos inscritos sem outro match têm nome repetido na base.
with sem_match as (
    select lower(strip_accents(trim(e.nome))) as nome_norm
    from inscritos_evento e
    left join casamento m using (inscricao_id)
    where m.inscricao_id is null
),
contagem as (
    select lower(strip_accents(nome)) as nome_norm, count(*) as n from pessoas group by 1
)
select
    count(*) as inscritos_sem_match,
    count(*) filter (where c.n > 1) as nome_com_homonimo_na_base,
    count(*) filter (where c.n is null) as nome_inexistente_na_base
from sem_match s
left join contagem c using (nome_norm);

-- name: funil_inscritos
-- Três réguas. Quem já era cliente antes do evento sai da conta de conversão.
-- A camada de nome entra só como "candidatos para revisar à mão": nome único na base não prova
-- que é a mesma pessoa (alguém de fora da base pode ter o mesmo nome).
with medir as (
    select r.regua, d.*
    from casamento m
    join (values (1, '1. só e-mail principal'), (3, '2. 3 camadas seguras'), (4, '3. + nome (revisar à mão)'))
         as r(ate_camada, regua) on m.camada <= r.ate_camada
    join desfecho_pessoa d using (pessoa_id)
)
select
    regua,
    count(*) as inscritos_identificados,
    count(*) filter (where ja_era_cliente) as ja_eram_clientes,
    count(*) filter (where agendou_depois and not coalesce(ja_era_cliente, false)) as agendaram_depois,
    count(*) filter (where comprou_depois and not coalesce(ja_era_cliente, false)) as compraram_depois,
    coalesce(sum(receita_depois) filter (where not coalesce(ja_era_cliente, false)), 0) as receita_depois
from medir
group by 1
order by 1;

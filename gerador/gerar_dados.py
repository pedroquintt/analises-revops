"""Gera o dataset sintético da operação comercial usado nos seis estudos.

Tudo é fictício e determinístico (seed 42). Os padrões que as análises
investigam foram plantados de propósito, com números inventados:

- reembolso concentrado na 1ª semana, mais alto em venda parcelada decidida na
  1ª call e em call longa;
- estorno de 1ª parcela só passa a ser registrado a partir de abril;
- três closers registram quase todos os motivos de perda, e um deles entra em março;
- salas de reunião reutilizadas pelo mesmo closer em dias diferentes;
- piora do mix de leads (menos tier A) a partir de 15/04;
- inscritos de evento com e-mail, telefone e nome em formatos diferentes do CRM.

Uso: python gerador/gerar_dados.py [--saida dados]
"""
from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_PESSOAS = 18000
INICIO = pd.Timestamp("2025-01-01")
FIM = pd.Timestamp("2025-06-30 23:59")
DATA_REGISTRO_ESTORNO = pd.Timestamp("2025-04-01")
INICIO_MIX_PIOR = pd.Timestamp("2025-04-15")
DATA_EVENTO = pd.Timestamp("2025-05-20 19:00")

PRIMEIROS = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Giovana", "Heitor",
             "Iara", "João", "Karina", "Leandro", "Marina", "Nícolas", "Olívia", "Paulo",
             "Renata", "Sérgio", "Tânia", "Vítor", "Bianca", "César", "Débora", "Enzo",
             "Flávia", "Guilherme", "Helena", "Igor", "Juliana", "Kauã", "Larissa", "Murilo",
             "Natália", "Otávio", "Priscila", "Rafael", "Sabrina", "Thiago", "Valéria", "Wesley"]
SOBRENOMES = ["Almeida", "Barros", "Cardoso", "Dias", "Esteves", "Farias", "Gomes", "Hora",
              "Ivo", "Jardim", "Leite", "Macedo", "Neves", "Oliveira", "Peixoto", "Queiroz",
              "Rocha", "Siqueira", "Tavares", "Uchoa", "Vieira", "Xavier", "Zanetti", "Moura",
              "Brandão", "Coutinho", "Falcão", "Guimarães", "Lisboa", "Monteiro"]

SDRS = ["Iara Moreira", "Heitor Vasconcelos", "Renata Duarte", "Diego Fontes"]

# nome, atraso médio para entrar na sala (min), prob. de registrar motivo de perda,
# prob. de escolher "dinheiro" quando registra, data de entrada no time
CLOSERS = [
    ("Ana Prado", 1.5, 0.05, 0.40, "2025-01-01"),
    ("Bruno Teles", 3.0, 0.06, 0.40, "2025-01-01"),
    ("Carla Nunes", 6.0, 0.90, 0.85, "2025-01-01"),
    ("Fábio Rezende", 2.0, 0.85, 0.80, "2025-01-01"),
    ("Giovana Pires", 4.0, 0.05, 0.40, "2025-01-01"),
    ("Olívia Campos", 8.0, 0.04, 0.40, "2025-01-01"),
    ("Vítor Antunes", 2.5, 0.92, 0.90, "2025-03-01"),
    ("Tânia Lobo", 5.0, 0.05, 0.40, "2025-01-01"),
]

FAIXAS = ["sem_renda", "ate_3k", "3k_6k", "6k_10k", "acima_10k"]
P_FAIXA_ANTES = [0.10, 0.20, 0.30, 0.22, 0.18]
P_FAIXA_DEPOIS = [0.14, 0.30, 0.32, 0.15, 0.09]
TIER = {"sem_renda": "D", "ate_3k": "C", "3k_6k": "B", "6k_10k": "A", "acima_10k": "A"}
P_AGENDA = {"A": 0.55, "B": 0.42, "C": 0.25}
P_VENDA = {"A": 0.42, "B": 0.30, "C": 0.18}
ORIGENS = ["meta_ads", "google_ads", "organico", "indicacao", "linkedin_ads"]
P_ORIGEM = [0.45, 0.20, 0.18, 0.10, 0.07]


def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().replace(" ", ".")


def _sala(rng: np.random.Generator) -> str:
    letras = "abcdefghijkmnopqrstuvwxyz"
    partes = ["".join(rng.choice(list(letras), n)) for n in (3, 4, 3)]
    return "-".join(partes)


def _minuto(ts: pd.Timestamp) -> pd.Timestamp:
    return ts.floor("min")


def gerar(saida: Path) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    saida.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- vendedores
    vendedores = pd.DataFrame(
        [(f"V{i:02d}", nome, "sdr", None, None, None, "2025-01-01") for i, nome in enumerate(SDRS, 1)]
        + [(f"V{i:02d}", nome, "closer", atraso, reg, din, entrada)
           for i, (nome, atraso, reg, din, entrada) in enumerate(CLOSERS, len(SDRS) + 1)],
        columns=["vendedor_id", "nome", "cargo", "_atraso_medio", "_registra_perda",
                 "_escolhe_dinheiro", "entrada_time"],
    )
    vendedores["entrada_time"] = pd.to_datetime(vendedores["entrada_time"])
    closers = vendedores[vendedores.cargo == "closer"].reset_index(drop=True)
    salas = {c: [_sala(rng) for _ in range(3)] for c in closers.nome}

    # ------------------------------------------------------------------ pessoas
    segundos = (FIM - INICIO).total_seconds()
    toque = INICIO + pd.to_timedelta(np.sort(rng.uniform(0, segundos, N_PESSOAS)), unit="s")
    nomes, emails, fones = [], [], []
    for i in range(N_PESSOAS):
        nome = f"{rng.choice(PRIMEIROS)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"
        nomes.append(nome)
        emails.append(f"{_slug(nome)}{i}@example.com")
        fones.append(f"119{rng.integers(10_000_000, 99_999_999)}")
    pessoas = pd.DataFrame({
        "pessoa_id": [f"P{i:05d}" for i in range(1, N_PESSOAS + 1)],
        "nome": nomes, "email": emails, "telefone": fones,
        "primeiro_toque": toque.floor("min"),
        "origem": rng.choice(ORIGENS, N_PESSOAS, p=P_ORIGEM),
    })
    pessoas["faixa_salarial"] = [
        rng.choice(FAIXAS, p=P_FAIXA_DEPOIS if t >= INICIO_MIX_PIOR else P_FAIXA_ANTES)
        for t in pessoas.primeiro_toque
    ]
    pessoas["tier"] = pessoas.faixa_salarial.map(TIER)

    # e-mails secundários do mesmo contato (a pessoa usa outro e-mail na agenda ou na compra)
    contato = [(p, e, True) for p, e in zip(pessoas.pessoa_id, pessoas.email)]
    tem_alias = rng.random(N_PESSOAS) < 0.12
    alias = {}
    for idx in np.flatnonzero(tem_alias):
        p = pessoas.iloc[idx]
        alias[p.pessoa_id] = f"{_slug(p.nome.split()[0])}.pagamentos{idx}@example.net"
        contato.append((p.pessoa_id, alias[p.pessoa_id], False))
    contato_emails = pd.DataFrame(contato, columns=["pessoa_id", "email", "principal"])

    def email_usado(pid: str, p_alias: float) -> str:
        principal = pessoas.at[int(pid[1:]) - 1, "email"]
        if pid in alias and rng.random() < p_alias:
            return alias[pid]
        return principal

    # --------------------------------------------------- sessões de formulário (leads brutos)
    sessoes = []
    crm_primeiro = rng.random(N_PESSOAS) < 0.05  # o CRM viu a pessoa antes do formulário
    for idx, p in pessoas.iterrows():
        atraso_form = pd.Timedelta(days=int(rng.integers(1, 11))) if crm_primeiro[idx] else pd.Timedelta(0)
        sessoes.append((p.pessoa_id, p.email, p.primeiro_toque + atraso_form))
        if rng.random() < 0.12:
            sessoes.append((p.pessoa_id, p.email, p.primeiro_toque + pd.Timedelta(days=int(rng.integers(1, 21)))))
    sessoes_formulario = pd.DataFrame(sessoes, columns=["pessoa_id", "email", "criado_em"])
    sessoes_formulario = sessoes_formulario[sessoes_formulario.criado_em <= FIM]
    sessoes_formulario.insert(0, "sessao_id", [f"S{i:06d}" for i in range(1, len(sessoes_formulario) + 1)])
    sessoes_formulario = sessoes_formulario.drop(columns="pessoa_id")  # o formulário só conhece o e-mail

    # ------------------------------------------------------------------- deals
    deals, agendas, sessoes_sala, transcricoes = [], [], [], []
    compras, transacoes, reembolsos = [], [], []
    motivos_descarte = ["sem experiência", "dados inválidos", "renda abaixo do perfil", "sem interesse"]
    outros_motivos = ["timing", "concorrente", "sem fit", "não respondeu"]

    compradores: set[str] = set()

    def novo_id(prefixo: str, lista: list) -> str:
        return f"{prefixo}{len(lista) + 1:06d}"

    for idx, p in pessoas.iterrows():
        if p.tier == "D":
            continue  # o bot de qualificação não cria deal para "sem renda"
        n_deals = 2 if rng.random() < 0.08 else 1
        for k in range(n_deals):
            criado = p.primeiro_toque + pd.Timedelta(hours=float(rng.uniform(0, 48)))
            if k == 1:
                criado += pd.Timedelta(days=int(rng.integers(5, 41)))
            if criado > FIM:
                continue
            sem_email = rng.random() < 0.04
            deal = {
                "deal_id": novo_id("D", deals), "email": None if sem_email else p.email,
                "nome_deal": f"[Pós] {p.nome} - {p.email}" if sem_email else f"[Pós] {p.nome}",
                "criado_em": _minuto(criado), "pipeline": "pre_vendas",
                "sdr": rng.choice(SDRS), "closer": None, "win": None,
                "fechado_em": None, "motivo_perda": None,
            }
            deals.append(deal)
            if k == 1:
                continue  # deal duplicado da mesma pessoa: fica parado em pré-vendas
            if rng.random() < 0.21:  # SDR descarta
                deal.update(win=False, motivo_perda=rng.choice(motivos_descarte),
                            fechado_em=_minuto(criado + pd.Timedelta(days=int(rng.integers(1, 6)))))
                continue
            if rng.random() >= P_AGENDA[p.tier]:
                if rng.random() < 0.5:
                    deal.update(win=False, motivo_perda="não respondeu",
                                fechado_em=_minuto(criado + pd.Timedelta(days=int(rng.integers(3, 20)))))
                continue

            # ------------------------------------------------------------ agenda
            dia = (criado + pd.Timedelta(days=int(rng.integers(1, 8)))).normalize()
            inicio = dia + pd.Timedelta(hours=int(rng.integers(9, 21)), minutes=int(rng.choice([0, 30])))
            if inicio > FIM:
                continue
            ativos = closers[closers.entrada_time <= inicio]
            c = ativos.iloc[int(rng.integers(0, len(ativos)))]
            deal.update(pipeline="vendas", closer=c.nome)
            sala = rng.choice(salas[c.nome])
            agenda_id = novo_id("A", agendas)
            agendas.append({"agenda_id": agenda_id, "email_convidado": email_usado(p.pessoa_id, 0.6),
                            "closer": c.nome, "inicio_agendado": inicio, "codigo_sala": sala})

            compareceu = rng.random() < 0.76
            atraso = float(np.clip(rng.normal(c._atraso_medio, c._atraso_medio * 0.8), -5, 40))
            if rng.random() < 0.05:
                atraso = float(rng.uniform(10, 25))
            entrada_vend = _minuto(inicio + pd.Timedelta(minutes=atraso))
            if compareceu:
                duracao = float(np.clip(rng.normal(55, 18), 8, 120))
            else:
                duracao = float(rng.uniform(3, 15))
            saida_vend = entrada_vend + pd.Timedelta(minutes=duracao)
            sessoes_sala.append({"codigo_sala": sala, "participante": "vendedor",
                                 "entrada": entrada_vend, "saida": _minuto(saida_vend)})
            if compareceu:
                entrada_lead = _minuto(inicio + pd.Timedelta(minutes=float(np.clip(rng.normal(1, 2), -3, 10))))
                sessoes_sala.append({"codigo_sala": sala, "participante": "lead",
                                     "entrada": entrada_lead, "saida": _minuto(saida_vend)})
            realizada = compareceu and duracao >= 20
            if not realizada:
                deal.update(win=False, motivo_perda="no-show" if not compareceu else None,
                            fechado_em=_minuto(inicio + pd.Timedelta(days=2)))
                continue

            vendeu = rng.random() < P_VENDA[p.tier]
            objecao = rng.random() < (0.12 if vendeu else 0.42)
            transcricoes.append({"agenda_id": agenda_id, "objecao_dinheiro": objecao, "virou_venda": vendeu})
            if not vendeu:
                motivo = None
                if rng.random() < c._registra_perda:
                    motivo = "dinheiro" if rng.random() < c._escolhe_dinheiro else rng.choice(outros_motivos)
                deal.update(win=False, motivo_perda=motivo,
                            fechado_em=_minuto(inicio + pd.Timedelta(days=int(rng.integers(1, 10)))))
                continue

            # ----------------------------------------------------------- venda
            dias = 0 if rng.random() < 0.55 else int(rng.integers(1, 11))
            data_compra = _minuto(saida_vend + pd.Timedelta(days=dias))
            if data_compra > FIM:
                continue
            deal.update(win=True, fechado_em=data_compra)
            forma = rng.choice(["pix", "cartao_parcelado", "boleto_parcelado"], p=[0.30, 0.45, 0.25])
            valor = float(rng.integers(70, 121) * 100)
            compra_id = novo_id("C", compras)
            compradores.add(p.pessoa_id)
            compras.append({"compra_id": compra_id, "email": email_usado(p.pessoa_id, 0.5),
                            "data_compra": data_compra, "forma_pagamento": forma, "valor": valor,
                            "agenda_id": agenda_id})

            if forma == "pix" and rng.random() < 0.4:
                entrada_val = round(valor * 0.15, 2)
                partes = [(data_compra, entrada_val),
                          (data_compra + pd.Timedelta(days=int(rng.integers(1, 11))), valor - entrada_val)]
            elif forma == "boleto_parcelado":
                n = int(rng.integers(6, 13))
                partes = [(data_compra + pd.DateOffset(months=m), round(valor / n, 2)) for m in range(n)]
            else:
                partes = [(data_compra, valor)]
            for data_tx, val in partes:
                if data_tx <= FIM:
                    transacoes.append({"transacao_id": novo_id("T", transacoes), "compra_id": compra_id,
                                       "data": data_tx, "valor": val})

            # -------------------------------------------------------- reembolso
            parcelado = forma != "pix"
            if parcelado and dias == 0 and duracao >= 70:
                p_reemb = 0.30
            elif parcelado and dias == 0:
                p_reemb = 0.17
            elif parcelado:
                p_reemb = 0.06
            else:
                p_reemb = 0.03
            if rng.random() >= p_reemb:
                continue
            u = rng.random()
            atraso_dias = int(rng.integers(0, 8)) if u < 0.85 else int(rng.integers(8, 31)) if u < 0.97 else int(rng.integers(31, 61))
            solicitado = _minuto(data_compra + pd.Timedelta(days=atraso_dias, hours=float(rng.uniform(0, 12))))
            if solicitado > FIM:
                continue
            if parcelado:
                tipo = rng.choice(["estorno_primeira_parcela", "integral", "retido", "downsell"], p=[0.45, 0.40, 0.10, 0.05])
            else:
                tipo = rng.choice(["integral", "retido", "downsell"], p=[0.85, 0.10, 0.05])
            if tipo == "estorno_primeira_parcela" and solicitado < DATA_REGISTRO_ESTORNO:
                continue  # o processo ainda não registrava esse tipo
            motivo = rng.choice(["arrependimento da compra", "não era o momento", "achou caro",
                                 "problema pessoal", "conteúdo diferente do esperado"],
                                p=[0.34, 0.26, 0.18, 0.14, 0.08])
            reembolsos.append({"reembolso_id": novo_id("R", reembolsos), "compra_id": compra_id,
                               "solicitado_em": solicitado, "tipo": tipo, "motivo": motivo})

    # ruído na sala: reuniões internas e treinamentos na mesma sala, em outros dias
    for c in closers.nome:
        for sala in salas[c]:
            for _ in range(int(rng.integers(6, 15))):
                dia = INICIO + pd.Timedelta(days=int(rng.integers(0, 180)), hours=int(rng.integers(8, 20)))
                sessoes_sala.append({"codigo_sala": sala, "participante": "vendedor", "entrada": dia,
                                     "saida": dia + pd.Timedelta(minutes=int(rng.integers(15, 60)))})

    # ------------------------------------------------- lista de inscritos de evento
    candidatos = pessoas[pessoas.primeiro_toque < DATA_EVENTO]
    escolhidos = candidatos.sample(330, random_state=SEED)
    inscritos, gabarito = [], []
    for _, p in escolhidos.iterrows():
        u = rng.random()
        fone_fmt = f"+55 ({p.telefone[:2]}) {p.telefone[2:7]}-{p.telefone[7:]}"
        if u < 0.55:
            linha = (p.nome, p.email.upper() if rng.random() < 0.3 else p.email, fone_fmt, "email")
        elif u < 0.70:
            linha = (p.nome, f"{_slug(p.nome.split()[0])}{rng.integers(100, 999)}@example.org", fone_fmt, "telefone")
        elif u < 0.82 and p.pessoa_id in alias:
            linha = (p.nome, alias[p.pessoa_id], None, "email_secundario")
        elif u < 0.92:
            nome_var = unicodedata.normalize("NFKD", p.nome).encode("ascii", "ignore").decode().upper()
            linha = (nome_var, f"contato{rng.integers(1000, 9999)}@example.org", None, "nome")
        else:
            linha = (p.nome.split()[0], f"anon{rng.integers(1000, 9999)}@example.org", None, "sem_match")
        inscritos.append(linha[:3])
        gabarito.append((p.pessoa_id, linha[3]))
        # parte dos inscritos agenda e compra depois do evento, usando o e-mail que quiser
        if p.pessoa_id in compradores or rng.random() >= 0.14:
            continue
        inicio = (DATA_EVENTO.normalize() + pd.Timedelta(days=int(rng.integers(1, 9)))
                  + pd.Timedelta(hours=int(rng.integers(9, 21))))
        c = closers.iloc[int(rng.integers(0, len(closers)))]
        sala = rng.choice(salas[c.nome])
        agenda_id = novo_id("A", agendas)
        agendas.append({"agenda_id": agenda_id, "email_convidado": email_usado(p.pessoa_id, 0.6),
                        "closer": c.nome, "inicio_agendado": inicio, "codigo_sala": sala})
        entrada = _minuto(inicio + pd.Timedelta(minutes=float(rng.uniform(0, 6))))
        fim_call = entrada + pd.Timedelta(minutes=float(rng.uniform(30, 80)))
        sessoes_sala.append({"codigo_sala": sala, "participante": "vendedor", "entrada": entrada, "saida": _minuto(fim_call)})
        sessoes_sala.append({"codigo_sala": sala, "participante": "lead", "entrada": _minuto(inicio), "saida": _minuto(fim_call)})
        if rng.random() < 0.45:
            compra_id = novo_id("C", compras)
            data_compra = _minuto(fim_call + pd.Timedelta(days=int(rng.integers(0, 4))))
            valor = float(rng.integers(70, 121) * 100)
            compras.append({"compra_id": compra_id, "email": email_usado(p.pessoa_id, 0.7),
                            "data_compra": data_compra, "forma_pagamento": "cartao_parcelado",
                            "valor": valor, "agenda_id": agenda_id})
            transacoes.append({"transacao_id": novo_id("T", transacoes), "compra_id": compra_id,
                               "data": data_compra, "valor": valor})
    for i in range(90):
        nome = f"{rng.choice(PRIMEIROS)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"
        inscritos.append((nome, f"{_slug(nome)}.novo{i}@example.org", f"+55 (21) 9{rng.integers(1000, 9999)}-{rng.integers(1000, 9999)}"))
        gabarito.append((None, "pessoa_nova"))
    ordem = rng.permutation(len(inscritos))
    inscritos_evento = pd.DataFrame([inscritos[i] for i in ordem], columns=["nome", "email", "telefone"])
    inscritos_evento.insert(0, "inscricao_id", [f"I{i:04d}" for i in range(1, len(inscritos_evento) + 1)])
    gabarito_evento = pd.DataFrame([gabarito[i] for i in ordem], columns=["pessoa_id", "como_casa"])
    gabarito_evento.insert(0, "inscricao_id", inscritos_evento.inscricao_id)

    tabelas = {
        "vendedores": vendedores[["vendedor_id", "nome", "cargo", "entrada_time"]],
        "pessoas": pessoas.drop(columns=["faixa_salarial"]).assign(faixa_salarial=pessoas.faixa_salarial),
        "contato_emails": contato_emails,
        "sessoes_formulario": sessoes_formulario,
        "deals": pd.DataFrame(deals),
        "agendas": pd.DataFrame(agendas),
        "sessoes_sala": pd.DataFrame(sessoes_sala).sample(frac=1, random_state=SEED).reset_index(drop=True),
        "transcricoes_call": pd.DataFrame(transcricoes),
        "compras": pd.DataFrame(compras),
        "transacoes": pd.DataFrame(transacoes),
        "reembolsos": pd.DataFrame(reembolsos),
        "inscritos_evento": inscritos_evento,
        "_gabarito_evento": gabarito_evento,
    }
    for nome, df in tabelas.items():
        df.to_parquet(saida / f"{nome}.parquet", index=False)
    return tabelas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parents[1] / "dados")
    args = parser.parse_args()
    tabelas = gerar(args.saida)
    for nome, df in tabelas.items():
        print(f"{nome:<20} {len(df):>7} linhas")


if __name__ == "__main__":
    main()

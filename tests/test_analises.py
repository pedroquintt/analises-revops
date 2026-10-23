"""Cada estudo encontra o padrão que ele afirma no README."""
import pandas as pd

import run_all


# ---------------------------------------------------------------- 01 churn
def test_01_reembolso_concentrado_na_primeira_semana(r):
    t = r["01"]["tempo_ate_reembolso"].set_index("faixa")
    assert t.loc["0-7 dias", "pct"] >= 75


def test_01_grao_transacao_esconde_o_parcelado(r):
    g = r["01"]["grao_compra_vs_transacao"].set_index("forma_pagamento")
    assert g.loc["boleto_parcelado", "taxa_por_compra"] > 2 * g.loc["boleto_parcelado", "taxa_por_transacao"]


def test_01_perfil_parcelado_na_primeira_call_longa_e_o_pior(r):
    taxa = r["01"]["perfil_da_venda"].set_index("perfil").taxa_reembolso
    assert taxa.iloc[3] > taxa.iloc[2] > taxa.iloc[1]
    assert taxa.iloc[3] > 2 * taxa.iloc[0]


def test_01_filtro_oficial_subconta_e_registro_muda_em_abril(r):
    f = r["01"]["filtro_conta_churn"]
    assert (f.taxa_ampla >= f.taxa_conta_churn).all()
    assert (f.loc[f.mes < "2025-04", "estorno_primeira_parcela"] <= 1).all()
    assert (f.loc[f.mes >= "2025-04", "estorno_primeira_parcela"] >= 3).all()


# ---------------------------------------------------------------- 02 objeção
def test_02_crm_superestima_dinheiro(r):
    crm = r["02"]["crm_por_mes"].set_index("mes")
    call = r["02"]["transcricao_por_mes"].set_index("mes")
    assert ((crm.pct_dinheiro_crm - call.pct_dinheiro_call) >= 25).all()
    assert call.pct_dinheiro_call.max() - call.pct_dinheiro_call.min() < 8


def test_02_tres_closers_respondem_pelo_indicador(r):
    c = r["02"]["crm_por_closer"].sort_values("pct_do_total_dinheiro", ascending=False)
    assert c.pct_do_total_dinheiro.head(3).sum() >= 85


# ---------------------------------------------------------------- 03 pontualidade
def test_03_join_sem_janela_gera_atraso_impossivel(r):
    sem = r["03"]["join_sem_janela"].iloc[0]
    assert sem.maior_atraso_min > 24 * 60
    assert sem.sessoes_por_agenda > 10


def test_03_janela_deixa_uma_sessao_por_agenda(r):
    com = r["03"]["join_com_janela"].iloc[0]
    assert com.com_sessao_do_vendedor == com.agendas
    assert 0 <= com.menor_espera_min and com.maior_espera_min <= 45


# ---------------------------------------------------------------- 04 MQL
def test_04_mql_nunca_maior_que_lead(r):
    f = r["04"]["funil_mensal"]
    assert (f.mql_pessoa <= f.leads_pessoa).all()


def test_04_chave_de_contagem_muda_o_numero(r):
    k = r["04"]["chave_de_contagem"].iloc[0]
    assert k.por_deal > k.por_email_do_contato > k.por_pessoa_resolvida


def test_04_sem_renda_nao_vira_mql(r):
    q = r["04"]["o_que_vira_mql"].set_index("faixa_salarial")
    assert q.loc["sem_renda", "pct_mql"] == 0
    assert (q.drop(index="sem_renda").pct_mql > 95).all()


# ---------------------------------------------------------------- 05 tiers
def test_05_conversao_ordenada_por_tier(r):
    c = r["05"]["conversao_por_tier"].set_index("tier").conversao_pct
    assert c["A"] > c["B"] > c["C"] > c["D"]


def test_05_mix_antecede_a_receita(r):
    s = run_all.indice_semanal(r["05"]["indicador_semanal"])
    antecedencia = run_all.semana_de_queda(s, "idx_realizado") - run_all.semana_de_queda(s, "idx_esperado")
    assert antecedencia >= pd.Timedelta(weeks=3)


# ---------------------------------------------------------------- 06 evento
def test_06_camadas_tem_precisao(con, r, dados):
    gabarito = pd.read_parquet(dados / "_gabarito_evento.parquet")
    m = con.execute("select * from casamento").df().merge(gabarito, on="inscricao_id")
    precisao = (m.pessoa_id_x == m.pessoa_id_y).groupby(m.camada).mean()
    assert (precisao.loc[[1, 2, 3]] == 1).all()
    # nome único na base erra: gente de fora da base com o mesmo nome vira falso positivo
    assert precisao.loc[4] < 0.9


def test_06_tres_camadas_acham_mais_resultado_que_so_email(r):
    f = r["06"]["funil_inscritos"].set_index("regua")
    assert f.loc["2. 3 camadas seguras", "compraram_depois"] > f.loc["1. só e-mail principal", "compraram_depois"]
    assert f.loc["2. 3 camadas seguras", "ja_eram_clientes"] > 0

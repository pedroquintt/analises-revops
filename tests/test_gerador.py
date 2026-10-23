"""Invariantes do dataset sintético: chaves, relacionamentos, determinismo e anonimização."""
import pandas as pd
import pytest

import gerar_dados

CHAVES = {
    "pessoas": "pessoa_id", "deals": "deal_id", "agendas": "agenda_id", "compras": "compra_id",
    "transacoes": "transacao_id", "reembolsos": "reembolso_id", "inscritos_evento": "inscricao_id",
    "sessoes_formulario": "sessao_id", "vendedores": "vendedor_id",
}


def ler(dados, tabela):
    return pd.read_parquet(dados / f"{tabela}.parquet")


@pytest.mark.parametrize("tabela,chave", CHAVES.items())
def test_chave_unica_e_nao_nula(dados, tabela, chave):
    df = ler(dados, tabela)
    assert df[chave].notna().all()
    assert df[chave].is_unique


@pytest.mark.parametrize("filha,coluna,mae,chave", [
    ("compras", "agenda_id", "agendas", "agenda_id"),
    ("transacoes", "compra_id", "compras", "compra_id"),
    ("reembolsos", "compra_id", "compras", "compra_id"),
    ("transcricoes_call", "agenda_id", "agendas", "agenda_id"),
    ("contato_emails", "pessoa_id", "pessoas", "pessoa_id"),
])
def test_relacionamentos(dados, filha, coluna, mae, chave):
    assert ler(dados, filha)[coluna].isin(ler(dados, mae)[chave]).all()


def test_determinismo(tmp_path, dados):
    gerar_dados.gerar(tmp_path)
    for tabela in ("pessoas", "deals", "compras", "reembolsos", "inscritos_evento"):
        pd.testing.assert_frame_equal(ler(dados, tabela), ler(tmp_path, tabela))


def test_todo_email_e_ficticio(dados):
    emails = pd.concat([
        ler(dados, "contato_emails").email, ler(dados, "inscritos_evento").email,
        ler(dados, "compras").email, ler(dados, "agendas").email_convidado,
        ler(dados, "deals").email.dropna(),
    ])
    assert emails.str.lower().str.endswith(("@example.com", "@example.org", "@example.net")).all()


def test_reembolso_depois_da_compra(dados):
    m = ler(dados, "reembolsos").merge(ler(dados, "compras"), on="compra_id")
    assert (m.solicitado_em >= m.data_compra).all()


def test_estorno_primeira_parcela_so_registrado_a_partir_de_abril(dados):
    r = ler(dados, "reembolsos")
    estornos = r[r.tipo == "estorno_primeira_parcela"]
    assert len(estornos) > 0
    assert (estornos.solicitado_em >= gerar_dados.DATA_REGISTRO_ESTORNO).all()

"""Utilitários comuns: conexão DuckDB, carga do dataset e execução das consultas nomeadas.

Cada `consulta.sql` é dividido por marcadores `-- name: <nome>`; cada bloco é um SELECT
cujo resultado vira `resultados/<nome>.csv` na pasta do estudo.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"
ANALISES = RAIZ / "analises"
BASE_SQL = ANALISES / "_base.sql"

TABELAS = ["vendedores", "pessoas", "contato_emails", "sessoes_formulario", "deals", "agendas",
           "sessoes_sala", "transcricoes_call", "compras", "transacoes", "reembolsos",
           "inscritos_evento"]


def conectar(dados: Path = DADOS) -> duckdb.DuckDBPyConnection:
    """Abre um DuckDB em memória com uma view por tabela do dataset e as views de base."""
    con = duckdb.connect()
    for tabela in TABELAS:
        con.execute(f"create view {tabela} as select * from read_parquet('{dados / tabela}.parquet')")
    con.execute(BASE_SQL.read_text())
    return con


def consultas(arquivo: Path) -> list[tuple[str, str]]:
    """Separa um arquivo SQL em pares (nome, sql) pelos marcadores `-- name:`."""
    partes = re.split(r"^--\s*name:\s*(\S+)\s*$", arquivo.read_text(), flags=re.M)
    return [(nome, sql.strip().rstrip(";")) for nome, sql in zip(partes[1::2], partes[2::2])]


def rodar_estudo(con: duckdb.DuckDBPyConnection, pasta: Path, salvar: bool = True) -> dict[str, pd.DataFrame]:
    """Executa todas as consultas de um estudo e, opcionalmente, salva os CSVs de resultado.

    Blocos cujo nome começa com `_` (ex.: `_setup`) só criam views auxiliares e não geram CSV.
    """
    resultados = {}
    for nome, sql in consultas(pasta / "consulta.sql"):
        if nome.startswith("_"):
            con.execute(sql)
        else:
            resultados[nome] = con.execute(sql).df()
    if salvar:
        destino = pasta / "resultados"
        destino.mkdir(exist_ok=True)
        for antigo in destino.glob("*.csv"):
            antigo.unlink()
        for nome, df in resultados.items():
            df.to_csv(destino / f"{nome}.csv", index=False)
    return resultados


def estudos() -> list[Path]:
    return sorted(p for p in ANALISES.iterdir() if p.is_dir() and p.name[:2].isdigit())

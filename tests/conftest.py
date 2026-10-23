import pandas as pd
import pytest

import gerar_dados
import revops


@pytest.fixture(scope="session")
def dados(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("dados")
    gerar_dados.gerar(pasta)
    return pasta


@pytest.fixture(scope="session")
def con(dados):
    return revops.conectar(dados)


@pytest.fixture(scope="session")
def r(con) -> dict[str, dict[str, pd.DataFrame]]:
    """Resultados de todos os estudos, indexados pelo número ('01'...'06')."""
    return {p.name[:2]: revops.rodar_estudo(con, p, salvar=False) for p in revops.estudos()}

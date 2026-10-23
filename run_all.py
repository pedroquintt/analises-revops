"""Gera o dataset, roda as consultas dos seis estudos e salva resultados e gráficos.

Uso: python run_all.py
"""
from __future__ import annotations

import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import revops  # noqa: E402

COR = "#2563eb"
COR_2 = "#f97316"
CINZA = "#9ca3af"

plt.rcParams.update({
    "figure.figsize": (9, 4.8), "figure.dpi": 130, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 12,
    "axes.titlelocation": "left", "font.size": 10,
})


def _salvar(fig, pasta) -> None:
    fig.tight_layout()
    fig.savefig(pasta / "grafico.png")
    plt.close(fig)


def grafico_01(r: dict[str, pd.DataFrame], pasta) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6))
    t = r["tempo_ate_reembolso"]
    a.bar(t.faixa, t.pct, color=[COR, CINZA, CINZA])
    a.set_title("Quando o reembolso chega (% dos pedidos)")
    for x, y in zip(t.faixa, t.pct):
        a.text(x, y + 1, f"{y:.0f}%", ha="center")
    a.set_ylim(0, 100)
    p = r["perfil_da_venda"]
    rotulos = [s.split(". ", 1)[1] for s in p.perfil]
    b.barh(rotulos, p.taxa_reembolso, color=[CINZA, CINZA, COR, COR])
    b.invert_yaxis()
    b.set_title("Taxa de reembolso por perfil da venda (%)")
    for y, v in enumerate(p.taxa_reembolso):
        b.text(v + 0.3, y, f"{v:.1f}%", va="center")
    _salvar(fig, pasta)


def grafico_02(r: dict[str, pd.DataFrame], pasta) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6))
    crm, call = r["crm_por_mes"], r["transcricao_por_mes"]
    a.plot(crm.mes, crm.pct_dinheiro_crm, marker="o", color=COR_2, label="CRM: motivo registrado")
    a.plot(call.mes, call.pct_dinheiro_call, marker="o", color=COR, label="Call: objeção na transcrição")
    a.set_ylim(0, 100)
    a.set_title("% de perdas por dinheiro, duas réguas")
    a.legend(frameon=False, loc="lower left")
    c = r["crm_por_closer"].sort_values("pct_do_total_dinheiro")
    cores = [COR_2 if v > 10 else CINZA for v in c.pct_do_total_dinheiro]
    b.barh(c.closer, c.pct_do_total_dinheiro, color=cores)
    b.set_title("Quem registra \"dinheiro\" (% do total)")
    _salvar(fig, pasta)


def grafico_03(r: dict[str, pd.DataFrame], pasta) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6))
    d = r["distribuicao_espera"]
    a.bar(d.faixa, d.pct, color=[COR, COR, CINZA, COR_2, COR_2])
    a.set_title("Espera do lead até o vendedor entrar (% das calls)")
    a.tick_params(axis="x", rotation=15)
    base = r["linha_de_base_por_closer"]
    b.errorbar(base.closer, base.mediana_min, yerr=[[0] * len(base), base.p90_min - base.mediana_min],
               fmt="o", color=COR, ecolor=CINZA, capsize=4)
    b.set_title("Linha de base por vendedor: mediana e p90 (min)")
    b.tick_params(axis="x", rotation=35)
    _salvar(fig, pasta)


def grafico_04(r: dict[str, pd.DataFrame], pasta) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6))
    f = r["funil_mensal"]
    x = range(len(f))
    a.bar([i - 0.2 for i in x], f.leads_pessoa, width=0.4, color=CINZA, label="Leads (pessoa)")
    a.bar([i + 0.2 for i in x], f.mql_pessoa, width=0.4, color=COR, label="MQL (pessoa)")
    a.set_xticks(list(x), f.mes)
    a.set_title("Lead e MQL ancorados no primeiro toque")
    a.legend(frameon=False, loc="lower left")
    d = r["destino_do_mql"]
    rotulos = [s.split(". ", 1)[1] for s in d.destino]
    cores = [COR if s.startswith("1") else COR_2 if s.startswith("2") else CINZA for s in d.destino]
    b.barh(rotulos, d.pct, color=cores)
    b.invert_yaxis()
    b.set_title("Destino do MQL (% do primeiro deal)")
    _salvar(fig, pasta)


def indice_semanal(s: pd.DataFrame) -> pd.DataFrame:
    """Média móvel de 4 semanas, base fev-mar = 100, e a semana em que cada índice
    fica abaixo de 90 por duas semanas seguidas."""
    s = s.copy()
    s["semana"] = pd.to_datetime(s.semana)
    base = (s.semana >= "2025-02-03") & (s.semana < "2025-04-07")
    for col, nome in (("receita_esperada_dos_leads", "idx_esperado"), ("receita_realizada", "idx_realizado")):
        media = s[col].rolling(4).mean()
        s[nome] = media / media[base].mean() * 100
    return s


def semana_de_queda(s: pd.DataFrame, col: str) -> pd.Timestamp:
    abaixo = (s[col] < 90) & (s[col].shift(-1) < 90) & (s.semana >= "2025-04-01")
    return s.loc[abaixo, "semana"].iloc[0]


def grafico_05(r: dict[str, pd.DataFrame], pasta) -> None:
    s = indice_semanal(r["indicador_semanal"])
    s = s[s.semana >= "2025-02-03"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(s.semana, s.idx_esperado, color=COR, lw=2, label="Esperado pelos leads da semana (mix de tier)")
    ax.plot(s.semana, s.idx_realizado, color=COR_2, lw=2, label="Receita realizada")
    ax.axhline(90, color=CINZA, lw=0.8, ls="--")
    for col, cor in (("idx_esperado", COR), ("idx_realizado", COR_2)):
        q = semana_de_queda(s, col)
        ax.axvline(q, color=cor, lw=0.8, ls=":")
        ax.text(q, 112, q.strftime(" %d/%m"), color=cor)
    ax.set_ylim(65, 118)
    ax.set_title("Índice semanal (média móvel 4 semanas, fev-mar = 100)")
    ax.legend(frameon=False, loc="lower left")
    _salvar(fig, pasta)


def grafico_06(r: dict[str, pd.DataFrame], pasta) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6))
    c = r["resumo_camadas"]
    rotulos = [s.split(". ", 1)[1] for s in c.camada]
    a.barh(rotulos, c.inscritos, color=[COR, COR, COR, COR_2])
    a.invert_yaxis()
    a.set_title("Inscritos identificados por camada")
    f = r["funil_inscritos"]
    rotulos = [s.split(". ", 1)[1] for s in f.regua]
    x = range(len(f))
    b.bar([i - 0.2 for i in x], f.agendaram_depois, width=0.4, color=CINZA, label="agendaram depois")
    b.bar([i + 0.2 for i in x], f.compraram_depois, width=0.4, color=COR, label="compraram depois")
    b.set_xticks(list(x), rotulos)
    b.tick_params(axis="x", rotation=10)
    b.legend(frameon=False)
    b.set_title("Resultado do evento, por régua de match")
    b.legend(frameon=False)
    _salvar(fig, pasta)


GRAFICOS = {"01": grafico_01, "02": grafico_02, "03": grafico_03,
            "04": grafico_04, "05": grafico_05, "06": grafico_06}


def main() -> None:
    subprocess.run([sys.executable, str(revops.RAIZ / "gerador" / "gerar_dados.py")], check=True)
    con = revops.conectar()
    for pasta in revops.estudos():
        resultados = revops.rodar_estudo(con, pasta)
        GRAFICOS[pasta.name[:2]](resultados, pasta)
        print(f"ok  {pasta.name}: {len(resultados)} consultas, gráfico salvo")


if __name__ == "__main__":
    main()

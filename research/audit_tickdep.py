"""CLI: dependência em escala de tick e densidade, sobre `data/raw/`.

    .venv\\Scripts\\python.exe research\\audit_tickdep.py

Responde: **a dependência dos retornos de tick está confinada ao lag 1?**

Se estiver, a curva de subamostragem é determinada pelos dois extremos e o
piloto de dois pontos já bastou. Se não estiver, a curva medida diverge da
prevista pelos `γ_j` truncados, e essa divergência é o resultado.

Não escreve em `data/`. A série é de auditoria, em memória, direto de `raw/` —
mesma postura do `m1_from_ticks` em `sigma.py`.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.lib import microstructure as M  # noqa: E402
from research.lib import sessions as SESS  # noqa: E402
from research.lib.loader import read_raw  # noqa: E402
from research.lib.market_calendar import drop_holidays  # noqa: E402
from research.lib.sessions import apply_trading_mask  # noqa: E402
from research.lib.sigma import SESSOES_UTC  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Alvos do piloto de 2026-06 (critério 2). Reproduzi-los é pré-requisito para
# rodar os quatro anos: se não baterem, a discrepância é mais informativa que
# o resultado.
PILOTO = {"rv2_intra": 3.8409, "sigma2": 4.0264, "rho1": 0.0123}
PILOTO_TOL = 0.02


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "desconhecido"


def _pico_memoria_mb() -> float:
    """Pico de working set do processo. `psutil` porque as duas rotas de ctypes
    tentadas antes devolveram 0 nesta maquina."""
    try:
        import psutil
        return psutil.Process().memory_info().peak_wset / (1024 * 1024)
    except Exception:
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except Exception:
            return float("nan")


def coletar(raw_root: Path, log: logging.Logger) -> pd.DataFrame:
    """Percorre `raw/` partição a partição e acumula estatísticas por barra."""
    partes = sorted(raw_root.glob("year=*/month=*"))
    if not partes:
        raise FileNotFoundError(f"nenhuma partição em {raw_root}")

    pedacos, ticks_lidos, ticks_fer, ticks_fora = [], 0, 0, 0
    for parte in partes:
        ano = int(parte.parent.name.split("=")[1])
        mes = int(parte.name.split("=")[1])
        f = read_raw(raw_root, year=ano, month=mes, columns=["ts", "bid"])
        ticks_lidos += len(f)

        f, fer = drop_holidays(f)
        ticks_fer += sum(fer.values())
        f, fora = apply_trading_mask(f)
        ticks_fora += fora

        if f.empty:
            continue
        b = M.per_bar_stats(f["ts"], f["bid"])
        a = M.rv_adr0005(f["ts"], f["bid"])
        b = b.merge(a, on="bar_time", how="left")
        pedacos.append(b)
        log.info("%s: %d barras", parte.name, len(b))

    todas = pd.concat(pedacos, ignore_index=True)
    todas.attrs["ticks_lidos"] = ticks_lidos
    todas.attrs["ticks_feriado"] = ticks_fer
    todas.attrs["ticks_fora_sessao"] = ticks_fora
    return todas


def estratos(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Estratos do brief: ano, hora dentro de 2026, domingo à parte."""
    dow = bars["bar_time"].dt.dayofweek
    ano = bars["bar_time"].dt.year
    hora = bars["bar_time"].dt.hour
    dom = dow == 6

    out: dict[str, pd.DataFrame] = {}
    for a in sorted(ano.unique()):
        sel = (ano == a) & ~dom
        if sel.any():
            out[f"ano_{a}"] = bars[sel]
    if dom.any():
        out["domingo"] = bars[dom]
    for h in range(24):
        sel = (ano == 2026) & ~dom & (hora == h)
        if sel.any():
            out[f"2026_h{h:02d}"] = bars[sel]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-root", default=str(REPO / "data" / "raw"))
    ap.add_argument("--reports-dir", default=str(REPO / "reports"))
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--cache", default=None,
                    help="Parquet com as estatisticas por barra. Fora de data/: "
                         "e artefato de auditoria, nao camada do projeto.")
    ap.add_argument("--recoletar", action="store_true",
                    help="Ignorar o cache e reler raw/.")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("audit_tickdep")
    t0 = time.time()

    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)

    cache = Path(args.cache) if args.cache else None
    if cache and cache.exists() and not args.recoletar:
        bars = pd.read_parquet(cache)
        for k in ("ticks_lidos", "ticks_feriado", "ticks_fora_sessao"):
            bars.attrs[k] = int(bars[k].iloc[0]) if k in bars.columns else 0
        log.info("cache lido de %s: %d barras", cache, len(bars))
    else:
        bars = coletar(Path(args.raw_root), log)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            aux = bars.copy()
            for k in ("ticks_lidos", "ticks_feriado", "ticks_fora_sessao"):
                aux[k] = bars.attrs.get(k, 0)
            aux.to_parquet(cache, compression="zstd")
            log.info("cache escrito em %s", cache)
    log.info("total: %d barras", len(bars))

    cheias = bars[bars["n_ticks"] >= M.MIN_TICKS]
    log.info("com n>=%d: %d barras", M.MIN_TICKS, len(cheias))

    # --- critério 2: reproduzir o piloto antes de tudo ----------------------
    jun = cheias[
        (cheias["bar_time"].dt.year == 2026) & (cheias["bar_time"].dt.month == 6)
    ]
    g_jun = M.pool_gamma(jun)
    piloto = {
        "rv2_intra": float(jun["rv2_intra"].mean()),
        "rho1": float(g_jun[1] / g_jun[0]),
    }
    ok_piloto = all(
        abs(piloto[k] - PILOTO[k]) / abs(PILOTO[k]) <= PILOTO_TOL for k in piloto
    )
    log.info("piloto rv2_intra=%.4f (alvo %.4f) rho1=%.5f (alvo %.5f) -> %s",
             piloto["rv2_intra"], PILOTO["rv2_intra"], piloto["rho1"], PILOTO["rho1"],
             "OK" if ok_piloto else "DIVERGENTE")

    # --- γ_j por estrato, com erro-padrão -----------------------------------
    linhas_g = []
    est = estratos(cheias)
    for nome, sub in est.items():
        g = M.gamma_with_se(sub, n_boot=args.n_boot)
        if g.empty:
            continue
        g = g.reset_index()
        g.insert(0, "estrato", nome)
        linhas_g.append(g)
        log.info("gamma %s: %d barras", nome, len(sub))

    # Criterio 6: quartis pelos DOIS eixos -- n_ticks e n_changes. A pergunta e
    # qual deles descreve a escala da dependencia, e isso se responde vendo em
    # qual eixo rho_1 varia mais entre quartis.
    d26 = est.get("ano_2026")
    rho_por_eixo: dict[str, list[float]] = {}
    if d26 is not None and len(d26) > 4:
        for eixo in ("n_ticks", "n_changes"):
            q = pd.qcut(d26[eixo].rank(method="first"), 4,
                        labels=["q1", "q2", "q3", "q4"])
            rhos = []
            for rot in ["q1", "q2", "q3", "q4"]:
                sub = d26[q == rot]
                g = M.gamma_with_se(sub, n_boot=args.n_boot).reset_index()
                g.insert(0, "estrato", f"2026_{rot}_{eixo}")
                g.insert(1, "eixo", eixo)
                g.insert(2, "n_ticks_mediano", float(sub["n_ticks"].median()))
                g.insert(3, "n_changes_mediano", float(sub["n_changes"].median()))
                linhas_g.append(g)
                gp = M.pool_gamma(sub)
                rhos.append(float(gp[1] / gp[0]))
            rho_por_eixo[eixo] = rhos
            log.info("quartis por %s: rho_1 = %s", eixo,
                     " ".join(f"{r:+.4f}" for r in rhos))

    autocov = pd.concat(linhas_g, ignore_index=True)
    autocov.to_csv(reports / "autocov-tick.csv", index=False, lineterminator="\n")

    # --- curva de assinatura: medida vs prevista ----------------------------
    linhas_a = []
    for nome, sub in est.items():
        if not nome.startswith("ano_") and nome != "domingo":
            continue
        g = M.pool_gamma(sub)
        # MEDIA, nao mediana: RV_k medido e media sobre barras, entao a
        # previsao tem de ser sobre a mesma estatistica. Ver predict_rv().
        n_bar = float(sub["n_ticks"].mean())
        for k in M.K_GRID:
            linhas_a.append({
                "estrato": nome, "k": k,
                "n_medio": n_bar,
                "n_mediano": float(sub["n_ticks"].median()),
                "rv_medido": float(sub[f"rv_{k}"].mean()),
                "rv_previsto": M.predict_rv(g, n_bar, k),
                "n_barras": len(sub),
            })
    assinatura = pd.DataFrame(linhas_a)
    assinatura["erro_rel"] = assinatura["rv_medido"] / assinatura["rv_previsto"] - 1.0
    # A FORMA e o que a sessao pergunta. Normalizar em k=1 tira o nivel, que
    # depende de Cov(n, gamma_0) e nao da estrutura de dependencia.
    base = assinatura[assinatura["k"] == 1].set_index("estrato")
    assinatura["forma_medida"] = assinatura.apply(
        lambda r: r["rv_medido"] / base.loc[r["estrato"], "rv_medido"], axis=1)
    assinatura["forma_prevista"] = assinatura.apply(
        lambda r: r["rv_previsto"] / base.loc[r["estrato"], "rv_previsto"], axis=1)
    assinatura["erro_forma"] = assinatura["forma_medida"] / assinatura["forma_prevista"] - 1.0
    assinatura.to_csv(reports / "assinatura-variancia.csv", index=False, lineterminator="\n")

    # --- densidade de tick --------------------------------------------------
    dens_h = M.tick_density(bars, "hora").reset_index().rename(columns={"_b": "hora_utc"})
    dens_h.insert(0, "bucket", "hora")
    dens_s = M.tick_density(bars, "sessao").reset_index().rename(columns={"_b": "sessao"})
    dens_s.insert(0, "bucket", "sessao")
    dens = pd.concat([dens_h, dens_s], ignore_index=True)
    dens.to_csv(reports / "densidade-tick.csv", index=False, lineterminator="\n")

    _plot(assinatura, reports / "assinatura-variancia.png")

    rep_estrato = pd.DataFrame([
        {"estrato": nome, **M.repeated_bid_share(sub),
         "n_ticks_mediano": float(sub["n_ticks"].median()),
         "n_changes_mediano": float(sub["n_changes"].median())}
        for nome, sub in est.items()
        if nome.startswith("ano_") or nome == "domingo"
    ])

    md = _relatorio(bars, cheias, est, autocov, assinatura, dens, piloto, ok_piloto,
                    t0, args.n_boot, rho_por_eixo, rep_estrato)
    (reports / "dependencia-tick.md").write_text(md, encoding="utf-8", newline="\n")

    log.info("tempo %.1f s, pico de memoria %.0f MB", time.time() - t0, _pico_memoria_mb())
    log.info("relatorio: %s", reports / "dependencia-tick.md")
    return 0


def _plot(assinatura: pd.DataFrame, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    anos = [e for e in assinatura["estrato"].unique() if e.startswith("ano_")]
    fig, axes = plt.subplots(1, len(anos), figsize=(4 * len(anos), 4), sharex=True)
    if len(anos) == 1:
        axes = [axes]
    for ax, e in zip(axes, anos):
        s = assinatura[assinatura["estrato"] == e]
        ax.plot(s["k"], s["rv_medido"], "o-", label="medido")
        ax.plot(s["k"], s["rv_previsto"], "s--", label="previsto por γ")
        ax.set_xscale("log", base=2)
        ax.set_xticks(list(M.K_GRID))
        ax.set_xticklabels([str(k) for k in M.K_GRID])
        ax.set_title(e.replace("ano_", ""))
        ax.set_xlabel("k (ticks por amostra)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("RV_k  (USD²)")
    axes[0].legend()
    fig.suptitle("Curva de assinatura — medida vs prevista pelos γ_j truncados em lag 8")
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def _relatorio(bars, cheias, est, autocov, assinatura, dens, piloto, ok_piloto,
               t0, n_boot, rho_por_eixo, rep_estrato) -> str:
    rep = M.repeated_bid_share(bars)
    # so minutos adjacentes: depois da parada diaria o "gap" e de 62 minutos e
    # nao descreve microestrutura nenhuma
    gap = bars.loc[bars["minuto_adjacente"] & (bars["gap_fronteira_s"] > 0),
                   "gap_fronteira_s"]
    dur_media = 60.0 / bars["n_ticks"].median()

    L = [
        "# Dependência em escala de tick — XAUUSD bid sobre `data/raw/`",
        "",
        "> Gerado por `research/audit_tickdep.py`. Nenhum número aqui é estimativa.",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Commit | `{_commit()}` |",
        f"| Máscara: `REOPEN_SUMMER` | {SESS.REOPEN_SUMMER} min ({SESS.REOPEN_SUMMER // 60:02d}:{SESS.REOPEN_SUMMER % 60:02d}) |",
        f"| Máscara: `SUNDAY_OPEN_SUMMER` | {SESS.SUNDAY_OPEN_SUMMER} min ({SESS.SUNDAY_OPEN_SUMMER // 60:02d}:{SESS.SUNDAY_OPEN_SUMMER % 60:02d}) |",
        f"| Máscara: `WINTER_SHIFT_MIN` | {SESS.WINTER_SHIFT_MIN} min |",
        f"| Ticks lidos | {bars.attrs.get('ticks_lidos', 0):,} |",
        f"| Removidos por feriado | {bars.attrs.get('ticks_feriado', 0):,} |",
        f"| Removidos fora de sessão | {bars.attrs.get('ticks_fora_sessao', 0):,} |",
        f"| Barras M1 | {len(bars):,} |",
        f"| Barras com n ≥ {M.MIN_TICKS} | {len(cheias):,} ({100 * len(cheias) / len(bars):.1f}%) |",
        f"| Bootstrap | {n_boot} reamostragens, blocos de um dia |",
        f"| Tempo | {time.time() - t0:.0f} s |",
        f"| Pico de memória | {_pico_memoria_mb():.0f} MB |",
        "",
        "A máscara já esteve errada três vezes. As constantes acima existem para que,",
        "quando ela mudar a quarta, dê para saber se estes números precisam ser regerados.",
        "",
        "---",
        "",
        "## Critério 2 — reprodução do piloto de 2026-06",
        "",
        "| Grandeza | Medido | Piloto | Diferença |",
        "|---|---|---|---|",
        f"| `E[rv²]` intra-minuto | {piloto['rv2_intra']:.4f} | {PILOTO['rv2_intra']:.4f} | {100 * (piloto['rv2_intra'] / PILOTO['rv2_intra'] - 1):+.2f}% |",
        f"| `ρ₁` | {piloto['rho1']:+.5f} | {PILOTO['rho1']:+.5f} | {100 * (piloto['rho1'] / PILOTO['rho1'] - 1):+.2f}% |",
        "",
        ("**Piloto reproduzido.**" if ok_piloto else "**PILOTO NÃO REPRODUZIDO — ler antes do resto.**"),
        "",
        "A diferença em `ρ₁` é esperada e tem causa conhecida: o piloto usou",
        "`pandas.Series.autocorr`, que remove a média e não exclui os pares que cruzam a",
        "fronteira do minuto. Este módulo exclui, e não remove média — ver a docstring de",
        "`microstructure.py` para o porquê.",
        "",
        "---",
        "",
        "## Resultado principal — `γ_j` por estrato",
        "",
        "A pergunta da sessão se responde olhando se `γ_j` para `j ≥ 2` é distinguível de",
        "zero. Não por limiar: por erro-padrão.",
        "",
    ]

    for nome in [e for e in est if e.startswith("ano_") or e == "domingo"]:
        sub = autocov[autocov["estrato"] == nome]
        if sub.empty:
            continue
        g0 = float(sub[sub["lag"] == 0]["gamma"].iloc[0])
        L += [
            f"### `{nome}`",
            "",
            "| lag | γ_j | erro-padrão | γ_j/γ₀ | \\|t\\| |",
            "|---|---|---|---|---|",
        ]
        for _, r in sub.iterrows():
            t = abs(r["gamma"] / r["erro_padrao"]) if r["erro_padrao"] > 0 else np.nan
            L.append(
                f"| {int(r['lag'])} | {r['gamma']:+.3e} | {r['erro_padrao']:.3e} | "
                f"{r['gamma'] / g0:+.5f} | {t:.1f} |"
            )
        L.append("")

    L += [
        "## Curva de assinatura — medida contra prevista",
        "",
        "A previsão usa `E[RV_k] = (n−k)·γ₀ + (2(n−k)/k)·Σ(k−j)·γ_j`, com os `γ_j`",
        "medidos acima e **truncados no lag 8**. Para `k ≤ 9` a previsão é exata dado o",
        "modelo; para `k` maior ela assume `γ_j = 0` acima do lag 8.",
        "",
        "**É essa truncagem que a curva testa.** Divergência crescente com `k` significa",
        "dependência além do lag 8 — ou covariância não estacionária dentro do minuto.",
        "",
        "**A forma normalizada em `k=1` e o que responde a pergunta.** O nivel absoluto",
        "depende de `Cov(n, γ₀)` — minutos movimentados sao mais volateis — e nao da",
        "estrutura de dependencia. As duas ultimas colunas isolam a forma.",
        "",
        "| Estrato | k | n medio | RV medido | RV previsto | erro nivel | forma medida | forma prevista | erro forma |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in assinatura.iterrows():
        L.append(
            f"| {r['estrato']} | {int(r['k'])} | {r['n_medio']:.0f} | "
            f"{r['rv_medido']:.4f} | {r['rv_previsto']:.4f} | {100 * r['erro_rel']:+.1f}% | "
            f"{r['forma_medida']:.4f} | {r['forma_prevista']:.4f} | **{100 * r['erro_forma']:+.2f}%** |"
        )

    L += [
        "",
        "![assinatura](assinatura-variancia.png)",
        "",
        "---",
        "",
        "## Critério 5 — gap de fronteira",
        "",
        "O `rv` do ADR 0005 inclui o retorno que atravessa a fronteira do minuto; o piloto",
        "mediu só o intra-minuto. A diferença é o span faltante, e o brief prevê um gap",
        "médio de ~1,3 s a partir da decomposição do déficit de 4,61%.",
        "",
        "| Grandeza | Valor |",
        "|---|---|",
        f"| Gap de fronteira, média | {gap.mean():.3f} s |",
        f"| Gap de fronteira, mediana | {gap.median():.3f} s |",
        f"| Gap de fronteira, p95 | {gap.quantile(0.95):.3f} s |",
        f"| Intervalo médio entre ticks, `60/n` | {dur_media:.3f} s |",
        f"| Razão gap ÷ intervalo médio | {gap.mean() / dur_media:.2f} |",
        f"| Previsto pelo brief | ~1,3 s |",
        "",
        f"| `E[rv²]` intra-minuto (todas as barras) | {bars['rv2_intra'].mean():.4f} |",
        f"| `E[rv²]` ADR 0005, com fronteira | {bars['rv2_adr'].mean():.4f} |",
        f"| Acréscimo da fronteira | {100 * (bars['rv2_adr'].mean() / bars['rv2_intra'].mean() - 1):+.2f}% |",
        "",
        "---",
        "",
        "## Bids repetidos",
        "",
        "| Grandeza | Valor |",
        "|---|---|",
        f"| Ticks | {rep['n_ticks']:,.0f} |",
        f"| Retornos | {rep['n_retornos']:,.0f} |",
        f"| Retornos com bid alterado | {rep['n_changes']:,.0f} |",
        f"| **Fração de retornos exatamente zero** | **{100 * rep['fracao_repetidos']:.1f}%** |",
        "",
        "### Por estrato",
        "",
        "| Estrato | ticks (mediana) | mudanças (mediana) | retornos zero |",
        "|---|---|---|---|",
    ]
    for _, r in rep_estrato.iterrows():
        L.append(
            f"| {r['estrato']} | {r['n_ticks_mediano']:.0f} | {r['n_changes_mediano']:.0f} | "
            f"{100 * r['fracao_repetidos']:.1f}% |"
        )

    L += [
        "",
        "### Qual eixo descreve a escala da dependência",
        "",
        "Critério 6 do brief. `ρ₁ = γ₁/γ₀` por quartil, em cada eixo. A dependência",
        "**escala com** o eixo em que `ρ₁` varia mais entre quartis; o eixo em que ela fica",
        "plana não é o que a governa.",
        "",
        "| Eixo | q1 | q2 | q3 | q4 | amplitude |",
        "|---|---|---|---|---|---|",
    ]
    veredicto_eixo = "não determinado"
    if rho_por_eixo:
        amps = {}
        for eixo, rhos in rho_por_eixo.items():
            amp = max(rhos) - min(rhos)
            amps[eixo] = amp
            L.append("| `" + eixo + "` | "
                     + " | ".join(f"{r:+.4f}" for r in rhos)
                     + f" | **{amp:.4f}** |")
        vencedor = max(amps, key=amps.get)
        razao = amps[vencedor] / min(amps.values()) if min(amps.values()) > 0 else float("inf")
        veredicto_eixo = (
            f"**`{vencedor}`**, com amplitude {razao:.1f}× a do outro eixo"
            if razao >= 1.5 else
            "**indistinguível** — as amplitudes ficam a menos de 1,5× uma da outra, "
            "e os dois eixos são quase colineares"
        )
    L += [
        "",
        f"Veredicto: {veredicto_eixo}.",
        "",
        "Ressalva: os dois eixos são fortemente correlacionados por construção — mais ticks",
        "implicam mais mudanças. Amplitudes próximas não significam que a escolha é",
        "indiferente, apenas que **estes dados não separam os dois**.",
        "",
        "Retorno exatamente zero viola ruído iid por construção: o erro de cotação é o",
        "mesmo em dois ticks seguidos. E interage com `tick_imb`, que pelo ADR 0005",
        "*repete o sinal anterior se igual* — nessa fração dos ticks o sinal é copiado, o",
        "que é injeção mecânica de autocorrelação numa primitiva que `bars/` vai congelar.",
        "",
        "---",
        "",
        "## Densidade de tick",
        "",
        "Fecha a lacuna \"Densidade de tick por sessão\" da seção 8 do",
        "`REFERENCIA-XAUUSD.md`.",
        "",
        "| Sessão | Barras | p05 | mediana | p95 | mudanças (mediana) | abaixo de 128 |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in dens[dens["bucket"] == "sessao"].iterrows():
        L.append(
            f"| {r['sessao']} | {int(r['n_barras']):,} | {r['ticks_p05']:.0f} | "
            f"{r['ticks_mediana']:.0f} | {r['ticks_p95']:.0f} | {r['changes_mediana']:.0f} | "
            f"{int(r['abaixo_de_128']):,} |"
        )

    L += [
        "",
        "| Hora UTC | Barras | p05 | mediana | p95 | abaixo de 128 |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in dens[dens["bucket"] == "hora"].iterrows():
        L.append(
            f"| {int(r['hora_utc']):02d} | {int(r['n_barras']):,} | {r['ticks_p05']:.0f} | "
            f"{r['ticks_mediana']:.0f} | {r['ticks_p95']:.0f} | {int(r['abaixo_de_128']):,} |"
        )

    L += [
        "",
        "---",
        "",
        "## Ressalvas",
        "",
        "- **Este relatório não conclui sobre `η`.** O que se mede é a dependência",
        "  **líquida**: momento em escala de tick entra positivo, quique de cotação entra",
        "  negativo, e os dois não são separáveis com série de bid apenas. Nada aqui deve",
        "  ser lido como estimativa de ruído de cotação nem de spread efetivo.",
        "- **Faixas de sanidade são relato, nunca suspeita.** Nenhum número foi descartado",
        "  nem \"corrigido\" por estar fora do esperado.",
        "- **`γ_j` não remove média.** A média dos retornos de tick é de ordem `s²/n`;",
        "  removê-la nesta escala introduz mais viés do que corrige.",
        "- **A previsão da curva trunca no lag 8.** Para `k ∈ {16, 32, 64}` ela assume",
        "  ausência de dependência acima disso, e a divergência observada é o teste dessa",
        "  suposição — não um erro do ajuste.",
        "- **`raw/` é Dukascopy, não o broker.** O caminho de preço transplanta; a densidade",
        "  de tick é parcial e o spread não transplanta (`REFERENCIA-XAUUSD.md` seção 4).",
        "",
    ]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())

"""Issue 1 figures, rendered from outputs/tables so `make figures` never recomputes.

Style: weg.figures (primary #1B2A41, gold highlight for China, greys for context,
no titles, direct labels when more than one series).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from weg import figures as F

from . import common as C


def render_all(cfg: dict, tables_dir: Path, fig_dir: Path) -> list[Path]:
    made: list[Path] = []
    made += _loss_reappearance(cfg, tables_dir, fig_dir)
    made += _destination_gains(cfg, tables_dir, fig_dir)
    made += _unit_values(cfg, tables_dir, fig_dir)
    made += _china_shares(cfg, tables_dir, fig_dir)
    made += _cost(cfg, tables_dir, fig_dir)
    made += _province(cfg, tables_dir, fig_dir)
    made += _gap(cfg, tables_dir, fig_dir)
    made += _relief(cfg, tables_dir, fig_dir)
    return made


def _label(cfg, product):
    return cfg["products"][product]["label"]


def _loss_reappearance(cfg, tables_dir, fig_dir):
    rows = []
    for product in cfg["products"]:
        p = tables_dir / f"q1_{product}_{C.HEADLINE_CF}_shock_monthly.csv"
        if p.exists():
            m = pd.read_csv(p)
            rows.append({"product": _label(cfg, product), "matched": m["matched_t"].sum() / 1000, "never": m["never_resold_t"].sum() / 1000})
    if not rows:
        return []
    df = pd.DataFrame(rows)
    fig, ax = F.new_figure(6.5, 3.2)
    y = np.arange(len(df))
    ax.barh(y, df["matched"], color=F.GREY_DARK, height=0.6, label="Reappeared elsewhere")
    ax.barh(y, df["never"], left=df["matched"], color=F.PRIMARY, height=0.6, label="Never resold")
    ax.set_yticks(y, df["product"])
    ax.invert_yaxis()
    ax.set_xlabel("Thousand tonnes, shock window, counterfactual B")
    ax.grid(axis="x"); ax.grid(False, axis="y")
    for i, (a, b) in enumerate(zip(df["matched"], df["never"])):
        ax.text(a + b, i, f" {a + b:,.0f}", va="center", fontsize=8, color=F.TEXT_MUTED)
    ax.legend(loc="lower right")
    return list(F.save(fig, fig_dir, "q1_loss_reappearance"))


def _destination_gains(cfg, tables_dir, fig_dir):
    out = []
    for product in cfg["products"]:
        p = tables_dir / f"q1_{product}_{C.HEADLINE_CF}_shock_ranking.csv"
        if not p.exists():
            continue
        r = pd.read_csv(p)
        r = r[r["gain"] != 0].head(8).iloc[::-1]
        fig, ax = F.new_figure(6.5, 3.2)
        ax.barh(r["destination"], r["gain"] / 1000, color=[F.PRIMARY if g > 0 else F.GREY_LIGHT for g in r["gain"]], height=0.6)
        ax.axvline(0, color=F.GRID, linewidth=0.8)
        ax.set_xlabel(f"{_label(cfg, product)}: change vs counterfactual B, thousand tonnes, shock window")
        ax.grid(axis="x"); ax.grid(False, axis="y")
        out += list(F.save(fig, fig_dir, f"q1_destination_gains_{product}"))
    return out


def _unit_values(cfg, tables_dir, fig_dir):
    out = []
    china = cfg["markets"]["china"]
    for product in cfg["products"]:
        p = tables_dir / f"q2_{product}_unit_values_sa.csv"
        if not p.exists():
            continue
        sa = pd.read_csv(p, index_col="period")
        w = cfg["windows"][product]
        pre = sa.loc[w["pre"][0]: w["pre"][1]]
        idx = sa / pre.mean() * 100
        idx = idx.loc[C.P.shift(w["pre"][0], -12):]
        fig, ax = F.new_figure(6.5, 3.4)
        x = np.arange(len(idx))
        cols = [c for c in idx.columns if c not in (china, "benchmark_ex_china")][:3]
        for c, color in zip(cols, [F.PRIMARY, F.GREY_DARK, F.GREY_LIGHT]):
            ax.plot(x, idx[c], color=color, linewidth=1.6)
            last = idx[c].last_valid_index()
            if last is not None:
                ax.text(x[list(idx.index).index(last)] + 0.3, idx.loc[last, c], c, fontsize=8, color=color, va="center")
        if china in idx.columns:
            ax.plot(x, idx[china], color=F.HIGHLIGHT, linewidth=2.0)
            last = idx[china].last_valid_index()
            if last is not None:
                ax.text(x[list(idx.index).index(last)] + 0.3, idx.loc[last, china], china, fontsize=8, color=F.HIGHLIGHT, va="center")
        ev = list(idx.index).index(w["event_month"]) if w["event_month"] in idx.index else None
        if ev is not None:
            ax.axvline(ev, color=F.GRID, linewidth=1.0, linestyle="--")
        ticks = [i for i, pp in enumerate(idx.index) if pp.endswith("-01")]
        ax.set_xticks(ticks, [idx.index[i][:4] for i in ticks])
        ax.set_ylabel(f"{_label(cfg, product)}: SA unit value, pre-window mean = 100")
        out += list(F.save(fig, fig_dir, f"q2_unit_values_{product}"))
    return out


def _china_shares(cfg, tables_dir, fig_dir):
    out = []
    for product in cfg["products"]:
        p = tables_dir / f"q3_{product}_china_import_shares.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        pre = df[df.window == "pre"].set_index("partner")["share"]
        shock = df[df.window == "shock"].set_index("partner")["share"]
        if pre.empty or shock.empty:
            continue
        partners = pd.concat([pre, shock], axis=1).fillna(0.0).max(axis=1).sort_values(ascending=False).head(6).index
        fig, ax = F.new_figure(6.5, 3.2)
        y = np.arange(len(partners))
        ax.barh(y - 0.18, pre.reindex(partners).fillna(0) * 100, height=0.36, color=F.GREY_LIGHT, label="Pre window")
        ax.barh(y + 0.18, shock.reindex(partners).fillna(0) * 100, height=0.36, color=[F.HIGHLIGHT if p_ == "CAN" else F.PRIMARY for p_ in partners], label="Shock window")
        ax.set_yticks(y, partners); ax.invert_yaxis()
        ax.set_xlabel(f"{_label(cfg, product)}: share of China's imports by origin, % (China-reported)")
        ax.grid(axis="x"); ax.grid(False, axis="y"); ax.legend(loc="lower right")
        out += list(F.save(fig, fig_dir, f"q3_china_shares_{product}"))
    return out


def _cost(cfg, tables_dir, fig_dir):
    p = tables_dir / "q4_cost.csv"
    if not p.exists():
        return []
    df = pd.read_csv(p)
    df = df[df.window == "shock"]
    if df.empty:
        return []
    piv = df.pivot_table(index="product", columns="counterfactual", values="cost_cad", aggfunc="sum") / 1e6
    piv = piv.reindex(columns=[c for c in C.CF_ORDER if c in piv.columns])
    piv.index = [_label(cfg, p_) for p_ in piv.index]
    fig, ax = F.new_figure(6.5, 3.2)
    y = np.arange(len(piv))
    n = len(piv.columns)
    colors = [F.GREY_LIGHT, F.PRIMARY, F.GREY_DARK]
    for j, cf in enumerate(piv.columns):
        ax.barh(y + (j - (n - 1) / 2) * 0.26, piv[cf], height=0.24, color=colors[j % 3], label=f"Counterfactual {cf.replace('_prime', chr(8242))}")
    ax.set_yticks(y, piv.index); ax.invert_yaxis()
    ax.set_xlabel("Cost to Canada, CAD million, shock window")
    ax.grid(axis="x"); ax.grid(False, axis="y"); ax.legend(loc="lower right")
    return list(F.save(fig, fig_dir, "q4_cost_by_counterfactual"))


def _province(cfg, tables_dir, fig_dir):
    p = tables_dir / "q5_province_cost.csv"
    if not p.exists() or p.stat().st_size < 10:
        return []
    df = pd.read_csv(p)
    if df.empty:
        return []
    df = df[df.counterfactual == C.HEADLINE_CF]
    piv = df.pivot_table(index="province", columns="product", values="net_cost_cad", aggfunc="sum").fillna(0.0) / 1e6
    piv = piv.loc[piv.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = F.new_figure(6.5, 3.2)
    left = np.zeros(len(piv))
    colors = [F.PRIMARY, F.GREY_DARK, F.GREY_LIGHT, F.HIGHLIGHT]
    for j, prod in enumerate(piv.columns):
        ax.barh(piv.index, piv[prod], left=left, color=colors[j % 4], height=0.6, label=_label(cfg, prod))
        left += piv[prod].values
    ax.invert_yaxis()
    ax.set_xlabel("Net lost revenue by province of origin, CAD million, shock window, counterfactual B (value basis)")
    ax.grid(axis="x"); ax.grid(False, axis="y"); ax.legend(loc="lower right")
    return list(F.save(fig, fig_dir, "q5_province_cost"))


def _gap(cfg, tables_dir, fig_dir):
    p = tables_dir / "q5_gap.csv"
    if not p.exists() or p.stat().st_size < 10:
        return []
    df = pd.read_csv(p)
    if df.empty:
        return []
    out = []
    for product, sub in df.groupby("product"):
        fig, ax = F.new_figure(6.5, 3.0)
        x = np.arange(len(sub))
        ax.axhline(0, color=F.GRID, linewidth=1.0)
        ax.plot(x, sub["gap_cad_t"], color=F.PRIMARY, marker="o", markersize=4)
        ax.set_xticks(x, sub["period"], rotation=45, fontsize=7)
        ax.set_ylabel(f"{_label(cfg, product)}: new buyers minus China pre-event price, CAD/t")
        out += list(F.save(fig, fig_dir, f"q5_gap_{product}"))
    return out


def _relief(cfg, tables_dir, fig_dir):
    out = []
    china = cfg["markets"]["china"]
    for product in cfg["products"]:
        w = cfg["windows"][product]
        pa, pc = tables_dir / f"q1_{product}_actual_tonnes.csv", tables_dir / f"q1_{product}_cf_{C.HEADLINE_CF}_tonnes.csv"
        if not (pa.exists() and pc.exists()):
            continue
        a = pd.read_csv(pa, index_col="period")[china] / 1000
        c = pd.read_csv(pc, index_col="period")[china] / 1000
        start = C.P.shift(w["pre"][0], -12)
        a, c = a.loc[start:], c.loc[start:]
        fig, ax = F.new_figure(6.5, 3.2)
        x = np.arange(len(a))
        ax.plot(x, c, color=F.GREY_DARK, linewidth=1.6, linestyle="--")
        ax.plot(x, a, color=F.HIGHLIGHT, linewidth=2.0)
        ax.text(x[-1] + 0.3, a.iloc[-1], "actual", fontsize=8, color=F.HIGHLIGHT, va="center")
        ax.text(x[-1] + 0.3, c.iloc[-1], "counterfactual B", fontsize=8, color=F.GREY_DARK, va="center")
        for key in ("event_month",):
            if w[key] in a.index:
                ax.axvline(list(a.index).index(w[key]), color=F.GRID, linewidth=1.0, linestyle="--")
        if w.get("relief") and w["relief"][0] in a.index:
            ax.axvline(list(a.index).index(w["relief"][0]), color=F.GRID, linewidth=1.0, linestyle=":")
        ticks = [i for i, pp in enumerate(a.index) if pp.endswith("-01")]
        ax.set_xticks(ticks, [a.index[i][:4] for i in ticks])
        ax.set_ylabel(f"{_label(cfg, product)}: exports to China, thousand tonnes")
        out += list(F.save(fig, fig_dir, f"china_volume_{product}"))
    return out

"""Singapore financial-stress monitor.

    python monitor.py            # use cache if < 12h old
    python monitor.py --refresh  # force re-download
    python monitor.py --open     # open the dashboard afterwards
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

import pandas as pd

import config as C
import data
import model
import report

OUT = Path(__file__).parent / "output"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    print("下載／讀取資料")
    raw, missing = data.load_all(args.refresh)

    print("計算指標")
    stress, vuln, extras = model.build_features(raw)
    comp = model.composite(stress, vuln)
    fund = model.load_fundamentals()
    capex = pd.read_csv(model.MANUAL / "ai_capex.csv", comment="#")
    fund_trig = model.fundamentals_trigger(fund, comp.index)
    rules = model.run_rules(comp, fund_trig)
    print("擬合狀態模型")
    reg = model.regimes(comp)
    print("回測")
    ctx = {
        "stress": stress, "vuln": vuln, "extras": extras, "comp": comp, "rules": rules, "regimes": reg,
        "pca": model.pca_check(stress, comp),
        "fund": fund, "capex": capex, "curve": model.curve_flag(extras["t10y2y"]), "missing": missing,
        "pred": model.predictive_stats(comp, extras["sg_equity"]),
        "events": model.event_study(comp, extras["sg_equity"]),
        "backtest": model.strategy_backtest(comp, fund_trig, extras),
        "sens": model.sensitivity(comp, fund_trig, extras),
    }

    OUT.mkdir(exist_ok=True)
    path = OUT / "dashboard.html"
    path.write_text(report.build(ctx), encoding="utf-8")

    t = comp["composite_pct"].last_valid_index()
    state = rules["state"].loc[t]
    snapshot = {
        "week": str(t.date()),
        "state": state,
        "composite_pct": round(float(comp.at[t, "composite_pct"]), 4),
        "vulnerability_pct": round(float(comp.at[t, "vulnerability_pct"]), 4),
        "breadth_80": round(float(comp.at[t, "breadth_80"]), 4),
        "layers": {k: round(float(comp.at[t, f"layer_{k}"]), 4) for k in C.LAYERS},
        "regime": None if reg is None else {k: round(float(v), 4) for k, v in reg.iloc[-1].items()},
        "bank_confirm": bool(rules.at[t, "bank_confirm"]),
    }
    hist = OUT / "history.jsonl"
    prev = json.loads(hist.read_text().splitlines()[-1]) if hist.exists() and hist.stat().st_size else None
    with hist.open("a") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    print()
    print(f"週 {snapshot['week']}  狀態 {state}  綜合分位 {snapshot['composite_pct']:.0%}  "
          f"脆弱度 {snapshot['vulnerability_pct']:.0%}  廣度 {snapshot['breadth_80']:.0%}")
    for k, (label, _) in C.LAYERS.items():
        print(f"  {label:<24} {snapshot['layers'][k]:.0%}")
    if snapshot["regime"]:
        print("  狀態模型 " + " ".join(f"{k}{v:.0%}" for k, v in snapshot["regime"].items()))
    if prev and prev["state"] != state:
        print(f"\n*** 狀態改變：{prev['state']} → {state} ***")
    print(f"\n儀表板：{path}")
    if args.open:
        webbrowser.open(path.resolve().as_uri())


if __name__ == "__main__":
    main()

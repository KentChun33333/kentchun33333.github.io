"""Feature construction, composite stress index, regime model, rules and backtests."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import config as C

MANUAL = Path(__file__).parent / "manual"


# ---------------------------------------------------------------- features
def _w(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = pd.to_datetime(s.index)
    return s.sort_index().resample("W-FRI").last()


def _drawdown(px: pd.Series, window: int = 52) -> pd.Series:
    return 1.0 - px / px.rolling(window, min_periods=window // 2).max()


def _basket(prices: list[pd.Series]) -> pd.Series:
    """Equal-weight, daily-rebalanced index from dividend-adjusted prices."""
    rets = pd.concat([p.pct_change(fill_method=None) for p in prices], axis=1)
    rets = rets[rets.notna().any(axis=1)].mean(axis=1, skipna=True)
    return (1 + rets.fillna(0)).cumprod()


def build_features(raw: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    basket_d = _basket([raw["D05.SI"], raw["O39.SI"], raw["U11.SI"]])
    basket = _w(basket_d)
    sti = _w(raw["^STI"])
    spy, rsp, sox = _w(raw["SPY"]), _w(raw["RSP"]), _w(raw["^SOX"])
    baa, vix = _w(raw["BAA10Y"]), _w(raw["VIXCLS"])
    hkma = raw["HKMA"]

    def vol63(daily: pd.Series) -> pd.Series:
        r = daily.pct_change(fill_method=None)
        return _w(r.rolling(63, min_periods=40).std() * np.sqrt(252))

    stress = pd.DataFrame(
        {
            "baa_spread": baa,
            "baa_spread_chg13w": baa.diff(13),
            "stlfsi": _w(raw["STLFSI4"]),
            "nfci": _w(raw["NFCI"]),
            "ofr_fsi": _w(raw["OFR"]["OFR FSI"]),
            "ofr_funding": _w(raw["OFR"]["Funding"]),
            "vix": vix,
            "vix_term": _w(raw["^VIX"]) / _w(raw["^VIX3M"]),
            "usdsgd_13w": _w(raw["DEXSIUS"]).pct_change(13, fill_method=None),
            "usdhkd": _w(raw["DEXHKUS"]),
            "hibor_spread": _w(hkma["hibor_fixing_1m"]) - _w(raw["DTB4WK"]),
            "hk_agg_balance": -np.log(_w(hkma["closing_balance"]).clip(lower=1)),
            "sti_dd": _drawdown(sti),
            "sgbank_dd": _drawdown(basket),
            "sgbank_rel": -(np.log(basket) - np.log(sti)).diff(26),
            "sgbank_vol": vol63(basket_d),
            "sox_dd": _drawdown(sox),
            "spx_dd": _drawdown(spy),
        }
    )
    vuln = pd.DataFrame(
        {
            "sox_heat": np.log(sox).diff(52) - np.log(spy).diff(52),
            "concentration": np.log(spy / rsp).diff(52),
            "credit_complacency": -baa,
            "vol_complacency": -vix.rolling(26, min_periods=13).mean(),
        }
    )
    idx = stress.index.union(vuln.index)
    idx = idx[(idx >= "1986-01-01") & (idx <= pd.Timestamp.today() + pd.Timedelta(days=6))]
    stress = stress.reindex(idx).ffill(limit=C.FFILL_LIMIT_WEEKS)
    vuln = vuln.reindex(idx).ffill(limit=C.FFILL_LIMIT_WEEKS)

    # Equity used for outcomes: STI price returns before the bank basket exists, basket after.
    r_basket, r_sti = basket.pct_change(fill_method=None), sti.pct_change(fill_method=None)
    sg_ret = r_basket.reindex(idx).combine_first(r_sti.reindex(idx)).fillna(0)
    extras = {
        "sg_equity": (1 + sg_ret).cumprod(),
        "bank_basket": basket.reindex(idx),
        "bank_basket_start": basket.first_valid_index(),
        "t10y2y": _w(raw["T10Y2Y"]).reindex(idx).ffill(limit=C.FFILL_LIMIT_WEEKS),
        "tbill3m": _w(raw["DTB3"]).reindex(idx).ffill(),
        "last_obs": _last_observations(raw),
    }
    return stress, vuln, extras


def _last_observations(raw: dict) -> pd.Series:
    out = {}
    for k, v in raw.items():
        if isinstance(v, pd.DataFrame):
            out[k] = pd.to_datetime(v.dropna(how="all").index.max())
        else:
            out[k] = pd.to_datetime(v.dropna().index.max())
    return pd.Series(out).sort_values()


# ---------------------------------------------------------------- composite
def expanding_pct(s: pd.Series, min_periods: int = C.MIN_HISTORY_WEEKS) -> pd.Series:
    """Percentile of each value vs. all history up to that date (no look-ahead)."""
    x = s.dropna()
    return x.expanding(min_periods=min_periods).rank(pct=True).reindex(s.index)


def composite(stress: pd.DataFrame, vuln: pd.DataFrame) -> pd.DataFrame:
    pct = stress.apply(expanding_pct)
    layer_of = {c.key: c.layer for c in C.STRESS_COMPONENTS}
    layers = pd.DataFrame({lay: pct[[k for k, v in layer_of.items() if v == lay]].mean(axis=1) for lay in C.LAYERS})
    w = pd.Series({k: v[1] for k, v in C.LAYERS.items()})
    avail = layers.notna()
    raw = (layers.fillna(0) * w).sum(axis=1) / (avail * w).sum(axis=1)
    raw[pct.notna().sum(axis=1) < 3] = np.nan  # need >= 3 live components
    out = layers.add_prefix("layer_")
    out["composite_raw"] = raw
    out["composite_pct"] = expanding_pct(raw)
    out["breadth_80"] = (pct >= 0.8).sum(axis=1) / pct.notna().sum(axis=1).replace(0, np.nan)
    out["n_components"] = pct.notna().sum(axis=1)
    vpct = vuln.apply(expanding_pct)
    out["vulnerability_raw"] = vpct.mean(axis=1)
    out["vulnerability_pct"] = expanding_pct(out["vulnerability_raw"])
    return out.join(pct.add_prefix("pct_")).join(vpct.add_prefix("vpct_"))


def pca_check(stress: pd.DataFrame, comp: pd.DataFrame) -> dict:
    """Diagnostic only (full-sample fit => look-ahead): does PC1 agree with the composite?"""
    pct = stress.apply(expanding_pct).dropna()
    if len(pct) < 100:
        return {}
    z = (pct - pct.mean()) / pct.std()
    vals, vecs = np.linalg.eigh(np.cov(z.T.values))
    pc1 = pd.Series(z.values @ vecs[:, -1], index=z.index)
    corr = pc1.corr(comp["composite_raw"].reindex(pc1.index))
    if corr < 0:
        pc1, corr, vecs[:, -1] = -pc1, -corr, -vecs[:, -1]
    return {
        "start": pct.index[0],
        "explained": float(vals[-1] / vals.sum()),
        "corr": float(corr),
        "loadings": pd.Series(vecs[:, -1], index=stress.columns).sort_values(ascending=False),
    }


# ---------------------------------------------------------------- regimes
def regimes(comp: pd.DataFrame) -> pd.DataFrame | None:
    """3-state Markov-switching model on the composite; filtered (real-time) probabilities."""
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    y = comp["composite_raw"].dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = MarkovRegression(y, k_regimes=3, trend="c", switching_variance=True).fit(
                search_reps=20, disp=False
            )
        except Exception as exc:
            print(f"  ! regime model failed: {exc}")
            return None
    probs = res.filtered_marginal_probabilities
    probs = probs.values if hasattr(probs, "values") else np.asarray(probs)
    means = [res.params[f"const[{i}]"] for i in range(3)]
    order = np.argsort(means)
    names = ["平穩", "緊張", "危機"]
    return pd.DataFrame({names[j]: probs[:, i] for j, i in enumerate(order)}, index=y.index)


# ---------------------------------------------------------------- rules
def load_fundamentals() -> pd.DataFrame:
    path = MANUAL / "bank_fundamentals.csv"
    df = pd.read_csv(path, comment="#", parse_dates=["report_date"])
    return df.dropna(subset=["credit_cost_bp"]).sort_values(["bank", "report_date"])


def fundamentals_trigger(fund: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """True from a bank's report date if its credit cost >= level trigger or jumped QoQ."""
    trig = pd.Series(False, index=index)
    if fund.empty:
        return trig
    rule = C.RULES
    for _, g in fund.groupby("bank"):
        g = g.sort_values("report_date")
        hit = (g["credit_cost_bp"] >= rule["credit_cost_bp_trigger"]) | (
            g["credit_cost_bp"].diff() >= rule["credit_cost_qoq_bp_trigger"]
        )
        s = pd.Series(hit.values, index=g["report_date"]).groupby(level=0).last()
        trig |= s.reindex(index, method="ffill").eq(True)
    return trig


def run_rules(comp: pd.DataFrame, fund_trig: pd.Series, rules: dict = C.RULES) -> pd.DataFrame:
    pct = comp["composite_pct"]
    market_conf = comp["layer_banks"].pipe(expanding_pct) >= rules["bank_confirm_layer_pct"]
    confirm = market_conf | fund_trig.reindex(pct.index).fillna(False)
    state, states = "NORMAL", []
    for t in pct.index:
        p = pct.loc[t]
        if np.isnan(p):
            states.append(state)
            continue
        if state != "DEFENSIVE" and p >= rules["defensive_enter"] and confirm.loc[t]:
            state = "DEFENSIVE"
        elif state == "NORMAL" and p >= rules["caution_enter"]:
            state = "CAUTION"
        elif state != "NORMAL" and p < rules["normal_exit"]:
            state = "NORMAL"
        states.append(state)
    return pd.DataFrame(
        {"state": states, "bank_confirm_market": market_conf, "bank_confirm": confirm}, index=pct.index
    )


def curve_flag(t10y2y: pd.Series) -> pd.Series:
    """Un-inversion window: inverted at some point in last 2y and now positive."""
    return (t10y2y.rolling(104, min_periods=52).min() < 0) & (t10y2y > 0)


# ---------------------------------------------------------------- backtests
def forward_drawdown(px: pd.Series, h: int = C.OUTCOME_HORIZON_WEEKS) -> pd.Series:
    vals = px.values
    out = np.full(len(vals), np.nan)
    for i in range(len(vals) - h):
        out[i] = np.min(vals[i + 1 : i + h + 1]) / vals[i] - 1
    return pd.Series(out, index=px.index)


def predictive_stats(comp: pd.DataFrame, sg_equity: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hit rates by threshold, plus AUC vs. a naive baseline (current 52w drawdown of the
    same equity): the index only adds value if it beats 'already falling'."""
    fdd = forward_drawdown(sg_equity)
    df = pd.DataFrame({"pct": comp["composite_pct"], "naive": _drawdown(sg_equity), "fdd": fdd}).dropna()
    y = df["fdd"] <= -C.OUTCOME_DRAWDOWN
    rows = []
    for thr in (0.7, 0.8, 0.9, 0.95):
        s = df["pct"] >= thr
        # episodes: contiguous signal runs; success if outcome follows the episode start
        starts = s & ~s.shift(1, fill_value=False)
        ep = y[starts]
        rows.append(
            {
                "門檻": f">= {thr:.0%}",
                "訊號週數": int(s.sum()),
                "精確率 P(大跌|訊號)": y[s].mean() if s.any() else np.nan,
                "基準率 P(大跌)": y.mean(),
                "提升倍數": (y[s].mean() / y.mean()) if s.any() and y.mean() > 0 else np.nan,
                "召回率 P(訊號|大跌)": s[y].mean() if y.any() else np.nan,
                "訊號段數": int(starts.sum()),
                "段落命中率": ep.mean() if len(ep) else np.nan,
            }
        )
    auc_rows = []
    for label, sub in (("全樣本", df), ("2003 起（四層皆有效）", df.loc["2003-07":])):
        ys = sub["fdd"] <= -C.OUTCOME_DRAWDOWN
        ok = ys.nunique() == 2
        auc_rows.append({
            "期間": label,
            "AUC 綜合指數": roc_auc_score(ys, sub["pct"]) if ok else np.nan,
            "AUC 只看已跌多少": roc_auc_score(ys, sub["naive"]) if ok else np.nan,
            "週數": len(sub),
        })
    return pd.DataFrame(rows), pd.DataFrame(auc_rows)


def event_study(comp: pd.DataFrame, sg_equity: pd.Series) -> pd.DataFrame:
    pct = comp["composite_pct"]
    fdd = forward_drawdown(sg_equity)
    rows = []
    for name, d in C.EVENTS.items():
        t = pct.index[pct.index.get_indexer([pd.Timestamp(d)], method="bfill")[0]]
        win = pct.loc[t - pd.Timedelta(weeks=26) : t + pd.Timedelta(weeks=8)]
        hit = win[win >= C.RULES["caution_enter"]]
        lead = (hit.index[0] - t).days / 7 if len(hit) else np.nan
        rows.append(
            {
                "事件": name,
                "日期": t.date(),
                "當週分位": pct.loc[t],
                "前26週最高分位": pct.loc[t - pd.Timedelta(weeks=26) : t].max(),
                "首次>=80%（週，負=提前）": lead,
                "之後26週新加坡股最大回撤": fdd.loc[t],
            }
        )
    return pd.DataFrame(rows)


def _perf(nav: pd.Series) -> dict:
    r = nav.pct_change().dropna()
    yrs = len(r) / 52
    return {
        "年化報酬": nav.iloc[-1] ** (1 / yrs) - 1,
        "年化波動": r.std() * np.sqrt(52),
        "最大回撤": (nav / nav.cummax() - 1).min(),
        "Sharpe(無風險=0)": r.mean() / r.std() * np.sqrt(52),
    }


def strategy_backtest(comp, fund_trig, extras, rules=C.RULES) -> dict:
    """Bank basket total return vs. the rule set. Signal at week t acts on week t+1."""
    start = extras["bank_basket_start"] + pd.Timedelta(weeks=1)
    px = extras["bank_basket"].loc[start:].dropna()
    r = px.pct_change().fillna(0)
    cash_r = (extras["tbill3m"].reindex(r.index).ffill().fillna(0) / 100 / 52)
    state = run_rules(comp, fund_trig, rules)["state"].reindex(r.index).ffill().shift(1).fillna("NORMAL")

    expo = np.where(state == "DEFENSIVE", rules["defensive_floor"], 1.0)
    nav_rule = (1 + expo * r + (1 - expo) * cash_r).cumprod()
    nav_bh = (1 + r).cumprod()
    perf = pd.DataFrame({"買進持有": _perf(nav_bh), "規則": _perf(nav_rule)}).T

    # DCA: 1 unit / week. CAUTION & DEFENSIVE: contributions to cash. DEFENSIVE entry: sell to floor.
    h_plain = h_eq = h_cash = 0.0
    prev = "NORMAL"
    for t in r.index:
        h_plain = h_plain * (1 + r[t]) + 1
        h_eq *= 1 + r[t]
        h_cash *= 1 + cash_r[t]
        s = state[t]
        if s == "DEFENSIVE" and prev != "DEFENSIVE":
            sell = h_eq * (1 - rules["defensive_floor"])
            h_eq, h_cash = h_eq - sell, h_cash + sell
        if s == "NORMAL":
            h_eq, h_cash = h_eq + h_cash + 1, 0.0
        else:
            h_cash += 1
        prev = s
    dca = pd.DataFrame(
        {
            "總投入": [len(r), len(r)],
            "期末財富": [h_plain, h_eq + h_cash],
        },
        index=["定期定額（不停）", "定期定額＋規則"],
    )
    time_in = state.value_counts(normalize=True).reindex(["NORMAL", "CAUTION", "DEFENSIVE"]).fillna(0)
    return {"perf": perf, "nav": pd.DataFrame({"買進持有": nav_bh, "規則": nav_rule}), "dca": dca, "time_in": time_in, "start": r.index[0]}


def sensitivity(comp, fund_trig, extras) -> pd.DataFrame:
    rows = []
    for d_enter in (0.85, 0.90, 0.95):
        for floor in (0.25, 0.50, 0.75):
            rules = {**C.RULES, "defensive_enter": d_enter, "defensive_floor": floor}
            p = strategy_backtest(comp, fund_trig, extras, rules)["perf"].loc["規則"]
            rows.append({"防守門檻": d_enter, "保留比重": floor, "年化報酬": p["年化報酬"], "最大回撤": p["最大回撤"]})
    return pd.DataFrame(rows)

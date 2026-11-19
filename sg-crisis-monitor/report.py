"""Self-contained HTML dashboard (Plotly via CDN)."""

from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config as C

STATE_COLOR = {"NORMAL": "#2e7d32", "CAUTION": "#f9a825", "DEFENSIVE": "#c62828"}
STATE_ZH = {"NORMAL": "正常：照原計畫", "CAUTION": "警戒：暫停定期定額，新資金存現金", "DEFENSIVE": "防守：銀行股降到下限比重"}


def _fmt(df: pd.DataFrame, pct_cols=(), num_cols=(), digits=2) -> str:
    d = df.copy()
    for c in pct_cols:
        if c in d:
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.1%}")
    for c in num_cols:
        if c in d:
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{digits}f}")
    return d.to_html(index=False, border=0, classes="tbl", escape=True, na_rep="")


def _state_shapes(fig, states: pd.Series, row: int):
    s = states.dropna()
    if s.empty:
        return
    blocks = (s != s.shift()).cumsum()
    for _, g in s.groupby(blocks):
        st = g.iloc[0]
        if st == "NORMAL":
            continue
        fig.add_vrect(x0=g.index[0], x1=g.index[-1] + pd.Timedelta(weeks=1), fillcolor=STATE_COLOR[st],
                      opacity=0.15, line_width=0, row=row, col=1)


def build(ctx: dict) -> str:
    comp, rules_df, reg = ctx["comp"], ctx["rules"], ctx["regimes"]
    t = comp["composite_pct"].last_valid_index()
    now = comp.loc[t]
    state = rules_df["state"].loc[t]
    plot_start = "1995-01-01"

    # --- figure 1: composite + states + SG equity
    f1 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4], vertical_spacing=0.04,
                       specs=[[{"secondary_y": True}], [{}]])
    c = comp.loc[plot_start:]
    f1.add_trace(go.Scatter(x=c.index, y=c["composite_pct"], name="綜合壓力分位", line=dict(color="#111", width=1.5)), row=1, col=1)
    f1.add_trace(go.Scatter(x=c.index, y=c["vulnerability_pct"], name="脆弱度分位", line=dict(color="#7b1fa2", width=1, dash="dot")), row=1, col=1)
    eq = ctx["extras"]["sg_equity"].loc[plot_start:]
    f1.add_trace(go.Scatter(x=eq.index, y=eq, name="新加坡銀行籃子（2000前=STI）", line=dict(color="#1565c0", width=1)), row=1, col=1, secondary_y=True)
    for thr, col in ((C.RULES["caution_enter"], "#f9a825"), (C.RULES["defensive_enter"], "#c62828"), (C.RULES["normal_exit"], "#2e7d32")):
        f1.add_hline(y=thr, line=dict(color=col, dash="dash", width=1), row=1, col=1)
    _state_shapes(f1, rules_df["state"].loc[plot_start:], 1)
    for name, d in C.EVENTS.items():
        if pd.Timestamp(d) >= pd.Timestamp(plot_start):
            f1.add_vline(x=pd.Timestamp(d), line=dict(color="#999", width=0.7), row=1, col=1)
            f1.add_annotation(x=pd.Timestamp(d), y=1.04, text=name.split(" ")[0], showarrow=False, font=dict(size=9), row=1, col=1)
    for lay, (label, _) in C.LAYERS.items():
        f1.add_trace(go.Scatter(x=c.index, y=c[f"layer_{lay}"], name=label, line=dict(width=1)), row=2, col=1)
    f1.update_yaxes(type="log", secondary_y=True, row=1, col=1, showgrid=False, showticklabels=False, title="銀行籃子（對數）")
    f1.update_yaxes(range=[0, 1.08], row=1, col=1, secondary_y=False, title="分位")
    f1.update_yaxes(range=[0, 1], row=2, col=1, title="層平均分位")
    f1.update_layout(height=720, margin=dict(l=50, r=30, t=30, b=30), legend=dict(orientation="h", y=-0.08), hovermode="x unified")

    # --- figure 2: regime probabilities
    f2 = None
    if reg is not None:
        r = reg.loc[plot_start:]
        f2 = go.Figure()
        for name, col in zip(r.columns, ("#2e7d32", "#f9a825", "#c62828")):
            f2.add_trace(go.Scatter(x=r.index, y=r[name], name=name, stackgroup="one", line=dict(width=0, color=col)))
        f2.update_layout(height=300, margin=dict(l=50, r=30, t=30, b=30), yaxis=dict(range=[0, 1], title="即時（filtered）機率"), hovermode="x unified")

    # --- figure 3: backtest NAV
    bt = ctx["backtest"]
    f3 = go.Figure()
    for col in bt["nav"]:
        f3.add_trace(go.Scatter(x=bt["nav"].index, y=bt["nav"][col], name=col))
    f3.update_layout(height=320, yaxis_type="log", margin=dict(l=50, r=30, t=30, b=30), hovermode="x unified")

    # --- component table
    comp_rows = []
    for spec in C.STRESS_COMPONENTS + C.VULNERABILITY_COMPONENTS:
        src = ctx["stress"] if spec.layer != "vuln" else ctx["vuln"]
        pcol = ("pct_" if spec.layer != "vuln" else "vpct_") + spec.key
        s, p = src[spec.key], comp[pcol]
        last = s.last_valid_index()
        comp_rows.append({
            "層": C.LAYERS[spec.layer][0] if spec.layer in C.LAYERS else "脆弱度",
            "指標": spec.label,
            "最新值": s.get(t, np.nan),
            "分位": p.get(t, np.nan),
            "4週前分位": p.shift(4).get(t, np.nan),
            "資料最後日期": last.date() if last is not None else "",
            "說明": spec.note,
        })
    comp_tbl = pd.DataFrame(comp_rows)

    fresh = ctx["extras"]["last_obs"].rename("最後觀測日").to_frame()
    fresh["落後天數"] = (pd.Timestamp.today().normalize() - fresh["最後觀測日"]).dt.days
    fresh["最後觀測日"] = fresh["最後觀測日"].dt.date
    fresh = fresh.reset_index(names="資料")

    reg_now = "" if reg is None else " ／ ".join(f"{k} {v:.0%}" for k, v in reg.iloc[-1].items())
    curve = bool(ctx["curve"].get(t, False))
    pca = ctx["pca"]
    pca_txt = "" if not pca else (
        f"主成分檢查（{pca['start'].date()} 起，全樣本擬合，僅作診斷）：PC1 解釋 {pca['explained']:.0%} 變異，"
        f"與綜合指數相關係數 {pca['corr']:.2f}。權重最高：{', '.join(pca['loadings'].index[:4])}。"
    )

    pred, auc = ctx["pred"]
    fund = ctx["fund"]
    fund_html = "<p>尚未填入（manual/bank_fundamentals.csv）。目前銀行確認訊號只用市場隱含的第三層。</p>" if fund.empty else fund.to_html(index=False, border=0, classes="tbl")
    capex = ctx["capex"]
    if capex.empty:
        capex_html = "<p>尚未填入（manual/ai_capex.csv）。</p>"
    else:
        cx = capex.assign(**{"資本支出／雲端營收": capex["capex_usd_bn"] / capex["cloud_revenue_usd_bn"]})
        capex_html = cx.to_html(index=False, border=0, classes="tbl", float_format=lambda v: f"{v:.2f}")

    fig_html = lambda f, first=False: f.to_html(full_html=False, include_plotlyjs="cdn" if first else False)

    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>新加坡金融壓力監測</title>
<style>
body{{font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif;max-width:1200px;margin:24px auto;padding:0 16px;color:#222}}
h1{{margin-bottom:4px}} h2{{border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:36px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}} .card{{flex:1;min-width:180px;border:1px solid #ddd;border-radius:8px;padding:12px}}
.card .v{{font-size:28px;font-weight:600}} .muted{{color:#777;font-size:13px}}
.tbl{{border-collapse:collapse;font-size:13px;width:100%}} .tbl th,.tbl td{{border-bottom:1px solid #eee;padding:4px 8px;text-align:left}}
.state{{color:#fff;padding:2px 10px;border-radius:6px}}
</style></head><body>
<h1>新加坡金融壓力監測</h1>
<div class="muted">最新週：{t.date()}　產生時間：{pd.Timestamp.now():%Y-%m-%d %H:%M}　所有分位皆為「當時可得歷史」的擴張視窗分位，無前視偏差。</div>
{f'<p style="color:#c62828">本次無法取得：{html.escape("、".join(ctx["missing"]))}。這些指標未納入綜合指數，下次執行會自動重試。</p>' if ctx["missing"] else ""}

<h2>現況</h2>
<div class="cards">
<div class="card"><div class="muted">行動狀態</div><div class="v"><span class="state" style="background:{STATE_COLOR[state]}">{state}</span></div><div>{STATE_ZH[state]}</div></div>
<div class="card"><div class="muted">綜合壓力分位</div><div class="v">{now['composite_pct']:.0%}</div><div class="muted">警戒 ≥{C.RULES['caution_enter']:.0%}・防守 ≥{C.RULES['defensive_enter']:.0%}＋銀行確認・解除 &lt;{C.RULES['normal_exit']:.0%}</div></div>
<div class="card"><div class="muted">脆弱度分位（累積中的風險）</div><div class="v">{now['vulnerability_pct']:.0%}</div><div class="muted">高脆弱＋低壓力 = 波動率悖論，不是安全訊號</div></div>
<div class="card"><div class="muted">廣度：≥80% 分位的指標比例</div><div class="v">{now['breadth_80']:.0%}</div><div class="muted">{int(now['n_components'])} 個指標有效</div></div>
<div class="card"><div class="muted">狀態模型（即時機率）</div><div style="font-size:16px;margin-top:8px">{html.escape(reg_now)}</div></div>
<div class="card"><div class="muted">殖利率曲線解除倒掛窗口</div><div class="v">{'是' if curve else '否'}</div><div class="muted">10Y–2Y 近兩年曾倒掛且現已轉正</div></div>
</div>

<h2>綜合壓力指數、狀態與各層</h2>
{fig_html(f1, True)}
<p class="muted">{html.escape(pca_txt)}</p>

{"<h2>三狀態馬可夫轉換模型</h2>" + fig_html(f2) + "<p class='muted'>參數以全樣本估計；狀態機率為只用當時資料的 filtered 機率。</p>" if f2 is not None else ""}

<h2>指標明細</h2>
{_fmt(comp_tbl, pct_cols=("分位", "4週前分位"), num_cols=("最新值",), digits=3)}

<h2>手動基本面</h2>
<h3>三大銀行信用成本／不良率</h3>{fund_html}
<h3>雲端資本支出／營收</h3>{capex_html}

<h2>回測一：預測力（結果 = 未來 {C.OUTCOME_HORIZON_WEEKS} 週新加坡股最大回撤 ≥ {C.OUTCOME_DRAWDOWN:.0%}）</h2>
<p>AUC：0.5 = 擲硬幣。對照組「只看已跌多少」= 新加坡股目前距 52 週高點的回撤。綜合指數必須明顯勝過對照組，才代表它不只是在說「已經在跌的會繼續跌」。週資料高度重疊，有效樣本只有十來次危機，差距 0.02 以內視為沒有差別。</p>
{_fmt(auc, num_cols=("AUC 綜合指數", "AUC 只看已跌多少"), digits=3)}
{_fmt(pred, pct_cols=("精確率 P(大跌|訊號)", "基準率 P(大跌)", "召回率 P(訊號|大跌)", "段落命中率"), num_cols=("提升倍數",))}

<h2>回測二：歷史事件</h2>
{_fmt(ctx['events'], pct_cols=("當週分位", "前26週最高分位", "之後26週新加坡股最大回撤"), num_cols=("首次>=80%（週，負=提前）",), digits=0)}

<h2>回測三：規則 vs 買進持有（三大銀行等權含息，{bt['start'].date()} 起）</h2>
{fig_html(f3)}
{_fmt(bt['perf'].reset_index(names='策略'), pct_cols=("年化報酬", "年化波動", "最大回撤"), num_cols=("Sharpe(無風險=0)",))}
<p>狀態時間佔比：{'、'.join(f'{k} {v:.0%}' for k, v in bt['time_in'].items())}。現金報酬用美國 3 個月國庫券代替（新加坡國庫券無免費長序列）。</p>
{bt['dca'].reset_index(names='方案').to_html(index=False, border=0, classes='tbl', float_format=lambda v: f'{v:,.0f}')}
<h3>參數敏感度（門檻未經優化；看結果是否在鄰近參數下仍穩定）</h3>
{_fmt(ctx['sens'], pct_cols=("年化報酬", "最大回撤"), num_cols=("防守門檻", "保留比重"))}

<h2>資料新鮮度</h2>
{fresh.to_html(index=False, border=0, classes='tbl')}
</body></html>"""

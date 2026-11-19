"""Indicator definitions, crisis events and action-rule thresholds.

Every stress component is oriented so that HIGHER = MORE STRESS.
Normalisation is an expanding-window percentile rank (no look-ahead).
"""

from dataclasses import dataclass

MIN_HISTORY_WEEKS = 156  # 3 years before a percentile is trusted
FFILL_LIMIT_WEEKS = 4  # tolerate publication lag (FRED FX ~1w, NFCI/STLFSI weekly)


@dataclass(frozen=True)
class Component:
    key: str
    layer: str
    label: str
    note: str


# Layer weights for the stress composite (renormalised over available layers).
LAYERS = {
    "global": ("L1 全球資金壓力", 0.35),
    "regional": ("L2 新加坡／香港", 0.25),
    "banks": ("L3 新加坡銀行（市場隱含）", 0.25),
    "ai": ("L4 AI／半導體修正", 0.15),
}

STRESS_COMPONENTS = [
    Component("baa_spread", "global", "Baa – 10Y 公債利差", "FRED BAA10Y，1986–；取代只剩 3 年歷史的 FRED 高收益債 OAS"),
    Component("baa_spread_chg13w", "global", "Baa 利差 13 週變化", "利差急升比水準更早反映壓力"),
    Component("stlfsi", "global", "聖路易聯準會金融壓力指數", "FRED STLFSI4"),
    Component("nfci", "global", "芝加哥聯準會 NFCI", "FRED NFCI"),
    Component("ofr_fsi", "global", "OFR 金融壓力指數", "financialresearch.gov"),
    Component("ofr_funding", "global", "OFR 資金子指數（美元融資）", "含交叉貨幣基差、Libor-OIS 類指標；免費的美元融資壓力替代"),
    Component("vix", "global", "VIX", "FRED VIXCLS"),
    Component("vix_term", "global", "VIX / VIX3M（>1 = 逆價差）", "Yahoo ^VIX、^VIX3M，2006–"),
    Component("usdsgd_13w", "regional", "USD/SGD 13 週變化（新幣走弱）", "FRED DEXSIUS"),
    Component("usdhkd", "regional", "USD/HKD 水準（靠近 7.85 弱方保證）", "FRED DEXHKUS"),
    Component("hibor_spread", "regional", "HIBOR 1M – 美國 4 週國庫券", "HKMA API + FRED DTB4WK"),
    Component("hk_agg_balance", "regional", "香港總結餘（越低越緊）", "HKMA closing_balance，取負對數"),
    Component("sti_dd", "regional", "STI 距 52 週高點回撤", "Yahoo ^STI"),
    Component("sgbank_dd", "banks", "三大銀行等權籃子 52 週回撤", "D05/O39/U11 還原股價"),
    Component("sgbank_rel", "banks", "銀行籃子 vs STI 26 週相對弱勢", "銀行跑輸大盤 = 市場在定價銀行風險"),
    Component("sgbank_vol", "banks", "銀行籃子 63 日已實現波動", "年化"),
    Component("sox_dd", "ai", "費城半導體 52 週回撤", "Yahoo ^SOX"),
    Component("spx_dd", "ai", "S&P 500 52 週回撤", "Yahoo SPY"),
]

# Vulnerability = build-up of fragility (volatility paradox), NOT current stress.
VULNERABILITY_COMPONENTS = [
    Component("sox_heat", "vuln", "半導體 vs S&P 500 52 週超額報酬", "AI 主題過熱程度"),
    Component("concentration", "vuln", "SPY / RSP 52 週變化（權值集中）", "市值加權跑贏等權 = 集中度上升"),
    Component("credit_complacency", "vuln", "信用利差過窄（Baa 利差反向）", "利差越低，風險定價越鬆"),
    Component("vol_complacency", "vuln", "VIX 26 週均值過低（反向）", "長期低波動常伴隨槓桿累積"),
]

# Crisis / shock onset dates used for event studies.
EVENTS = {
    "1997 亞洲金融風暴": "1997-07-02",
    "1998 LTCM／俄羅斯": "1998-08-17",
    "2000 科網泡沫破裂": "2000-03-10",
    "2007 次貸／BNP 凍結基金": "2007-08-09",
    "2008 雷曼倒閉": "2008-09-15",
    "2011 美債降評／歐債": "2011-08-05",
    "2015 人民幣貶值": "2015-08-11",
    "2018 Q4 緊縮恐慌": "2018-10-03",
    "2020 疫情": "2020-02-21",
    "2022 升息熊市": "2022-01-03",
    "2023 SVB／瑞信": "2023-03-10",
}

# Action rules (written in calm times; executed mechanically).
RULES = {
    "caution_enter": 0.80,  # composite percentile: pause DBS DCA, accumulate cash
    "defensive_enter": 0.90,  # + bank confirmation: cut banks to floor weight
    "normal_exit": 0.50,  # hysteresis: only return to plan below this
    "bank_confirm_layer_pct": 0.80,  # market-implied bank-layer percentile
    "credit_cost_bp_trigger": 40.0,  # manual fundamentals: credit cost level
    "credit_cost_qoq_bp_trigger": 10.0,  # manual fundamentals: QoQ rise
    "defensive_floor": 0.50,  # fraction of bank holdings kept in DEFENSIVE
}

# Backtest outcome definition.
OUTCOME_HORIZON_WEEKS = 26
OUTCOME_DRAWDOWN = 0.20

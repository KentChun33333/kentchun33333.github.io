# 新加坡金融壓力監測

每週一次，從免費公開資料計算綜合壓力指數、狀態機率和行動狀態，輸出互動式儀表板 `output/dashboard.html`。不需要 API key。

```bash
cd sg-crisis-monitor
python3 monitor.py            # 快取 12 小時內有效
python3 monitor.py --refresh  # 強制重新下載
python3 monitor.py --open     # 跑完直接開儀表板
```

需要套件：`pandas numpy requests scikit-learn statsmodels plotly`。

## 方法

1. **方向統一**：每個指標都轉成「越高 = 越緊張」（例如香港總結餘取負對數，銀行相對 STI 的表現取負值）。
2. **標準化**：每週數值和「當時以前的全部歷史」比，算擴張視窗分位（至少 3 年歷史才啟用）。不用全樣本 z 分數，因為那會偷看未來。
3. **分層合成**：同層指標取平均，再依層權重合成（全球 35%、新加坡／香港 25%、銀行 25%、AI 15%），最後再對合成值算一次擴張分位，得到 `composite_pct`。
4. **廣度**：≥80% 分位的指標佔比。單一指標飆高常是雜訊，多數一起升才可信。
5. **脆弱度指數**（與壓力分開）：半導體超額報酬、權值集中度、信用利差過窄、長期低波動。這些是「風險在累積」而不是「風險正在發生」；高脆弱＋低壓力就是波動率悖論的典型位置。
6. **狀態模型**：在綜合值上擬合三狀態馬可夫轉換模型（各狀態均值和變異數不同），報告只用當時資料的 filtered 機率。參數仍是全樣本估計，這點有前視成分，所以只作參考，不進入規則。
7. **PCA 檢查**：第一主成分和綜合指數的相關性。高相關代表加權方式不是任意選出來的結果。

## 行動規則（`config.py` 的 `RULES`）

| 狀態 | 進入條件 | 動作 |
|---|---|---|
| NORMAL | 綜合分位 < 50%（從其他狀態回來） | 照原計畫定期定額 |
| CAUTION | 綜合分位 ≥ 80% | 暫停定期定額，新資金存現金 |
| DEFENSIVE | 綜合分位 ≥ 90% **且** 銀行確認 | 銀行股降到 50% 下限比重 |

銀行確認＝第三層（銀行市場隱含壓力）分位 ≥ 80%，**或** `manual/bank_fundamentals.csv` 中任一銀行信用成本 ≥ 40bp、或單季上升 ≥ 10bp。

50% 的解除門檻刻意低於進入門檻，避免在 80% 附近來回進出。

**門檻沒有經過最佳化**，是在看回測之前就定好的。儀表板的敏感度表是用來確認結果在鄰近參數下不會崩掉，不是用來挑最好的那組。挑最好的那組就是過度擬合。

## 回測怎麼讀

- **預測力**：結果定義為未來 26 週新加坡股（2000 年前用 STI，之後用三大銀行等權含息籃子）最大回撤 ≥ 20%。看「提升倍數」和 AUC，不要看單一精確率。週資料高度重疊，真正獨立的危機只有十來次，統計誤差很大。AUC 表附對照組「只看目前距 52 週高點跌了多少」：2003 年後兩者幾乎相同（約 0.73 vs 0.72），代表指數多數預測力來自下跌的延續，而不是提前預警。
- **事件表**：負數代表訊號比事件早幾週出現。有些事件（例如 2020 疫情）是外生衝擊，任何指標都不會提前，這是正常的。
- **策略**：壓力指數是「同時」指標，主要價值是避開下跌的後半段和股息被砍的時期，而不是精準逃頂。若規則版本報酬略低但回撤明顯較小，就是設計目的。
- **早期樣本限制**：銀行籃子從 2000 年才有資料，加上 3 年暖機，第三層和銀行確認要到 2003 年才啟用，所以 2000–2003 年規則不可能進入 DEFENSIVE，規則版本的最大回撤就落在這段。1990 年代的分位只跟幾年歷史比較，容易長期偏高，事件表裡 1997–2000 的「提前」要打折看。

## 資料來源與限制

| 想看的東西 | 實際用的 | 原因 |
|---|---|---|
| 美國高收益債利差 | Baa–10Y 公債利差（FRED `BAA10Y`） | FRED 上的 ICE 高收益債 OAS 因授權只剩近 3 年，算不出可靠分位 |
| 交叉貨幣基差 | OFR 金融壓力指數的 Funding 子指數 | 基差需要 Bloomberg；OFR 子指數已包含相關成分 |
| SORA–SOFR 利差 | 未納入 | MAS API 不穩定（建置時正在維護），SOFR 也只有 2018 年起的資料 |
| S$NEER | USD/SGD 13 週變化 | MAS 不公布每日 S$NEER |
| 香港商用不動產、新加坡房價 | 未納入綜合指數 | 季資料、發布延遲長；請看 MAS 金融穩定報告 |
| 銀行信用成本、不良率 | `manual/bank_fundamentals.csv` | 只在季報裡；`report_date` 填公布日，回測才不會偷看未來 |
| 雲端資本支出／營收 | `manual/ai_capex.csv` | 同上 |

任何來源下載失敗時，該指標會從當次計算中排除，儀表板頂部會列出缺了哪些。HKMA API 會擋短時間內的大量請求（回 405），隔一段時間重跑即可；成功一次後就會使用快取。

## 每週自動執行（macOS launchd 範例）

`~/Library/LaunchAgents/com.sg-crisis-monitor.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.sg-crisis-monitor</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/env</string><string>python3</string>
    <string>/ABSOLUTE/PATH/sg-crisis-monitor/monitor.py</string><string>--refresh</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Weekday</key><integer>6</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/sg-crisis-monitor.log</string>
</dict></plist>
```

`launchctl load ~/Library/LaunchAgents/com.sg-crisis-monitor.plist`。每次執行都會在 `output/history.jsonl` 追加一筆快照，狀態改變時終端輸出會標示 `*** 狀態改變 ***`。

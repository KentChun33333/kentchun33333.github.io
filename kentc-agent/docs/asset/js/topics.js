// Topic list for the docs reader (index.html) and the standalone topic pages (topics/<slug>.html).
// Split into two top-level tabs:
//   - "agent": kentc_agent single-task engine (loop.py, context, compaction, LSM, tools, workflows)
//   - "breezeman": Breezeman long-horizon host (FastAPI, scheduler, global memory/Dreaming, Studio integration)
window.KENTC_TABS = [
  {
    "id": "agent",
    "label": "kentc_agent",
    "short": "單任務引擎",
    "desc": "單任務執行迴圈（loop.py）、上下文預算、前景主題壓縮、LSM 封存與文件解析"
  },
  {
    "id": "breezeman",
    "label": "Breezeman",
    "short": "長程常駐與記憶",
    "desc": "FastAPI 宿主、非同步排程與熔斷、全域記憶／Dreaming 蒸餾，以及 Folder-as-Studio 整合"
  }
];

window.KENTC_TOPICS = [
  // ==================== TAB 1: kentc_agent ====================
  {
    "tab": "agent", "slug": "layers", "num": "00", "nav": "使用層與權限", "group": "基礎：單任務引擎",
    "kicker": "同一個核心引擎，隨看管程度收斂權限",
    "title": "越無人看管，權限越收斂",
    "problem": "同一引擎服務 CLI 互動、無人看管工作流程，以及 Breezeman 內嵌的受限 Studio 資料夾。單一權限組不是過寬就是過窄。"
  },
  {
    "tab": "agent", "slug": "principles", "num": "01", "nav": "方法論", "group": "基礎：單任務引擎",
    "kicker": "先理解方法，再看模組",
    "title": "把任務拆成「證據、行動、控制、紀錄」",
    "problem": "小模型會宣稱已完成卻未寫檔、心算出錯、把推論寫成原文；只看回覆無法核對。"
  },
  {
    "tab": "agent", "slug": "loop", "num": "02", "nav": "執行迴圈（loop.py）", "group": "基礎：單任務引擎",
    "kicker": "任務如何真的往前走",
    "title": "一次 run 可以包含多個 operation",
    "problem": "單任務需數十次模型－工具往返；任一步可能截斷、中斷、跨日漂移，或重試堆疊重複指令。"
  },
  {
    "tab": "agent", "slug": "capabilities", "num": "03", "nav": "能力與策略", "group": "基礎：單任務引擎",
    "kicker": "誰決定上限，誰決定用法",
    "title": "伺服器能力 ≠ 代理設定",
    "problem": "各部署的視窗、影像能力、速率限制與連線行為不同；寫死數值或盲目重送會超限、重複或卡死。"
  },
  {
    "tab": "agent", "slug": "vertical", "num": "04", "nav": "上下文視窗", "group": "上下文管理、壓縮與單任務長程",
    "kicker": "上下文視窗的兩個方向",
    "title": "跨回合壓縮歷史；單回合控制新資料",
    "problem": "W ≈ 6 萬 tokens，單件審查案原始資料 ≈ 一個視窗；歷史逐輪累積（縱向），單次結果可一次塞滿（橫向）。"
  },
  {
    "tab": "agent", "slug": "documents", "num": "05", "nav": "文件解析", "group": "上下文管理、壓縮與單任務長程",
    "kicker": "橫向的極端：大型文件與影像",
    "title": "先轉換，再依預算解析；只接受完整結果",
    "problem": "單一 PDF、掃描檔或 Office 檔即可超過剩餘視窗；部分 PDF 只有佔位文字。直接注入不是放不下，就是讀錯。"
  },
  {
    "tab": "agent", "slug": "folders", "num": "06", "nav": "記憶分工", "group": "上下文管理、壓縮與單任務長程",
    "kicker": "工作區與工作階段，不是長期記憶系統",
    "title": "「存在哪裡」與「模型看得到什麼」是兩個問題",
    "problem": "「記憶」被混指檔案、對話紀錄與目前上下文；混用導致誤以為存過即可見。"
  },
  {
    "tab": "agent", "slug": "eval", "num": "07", "nav": "摘要 → 主題筆記", "group": "上下文管理、壓縮與單任務長程",
    "kicker": "長任務的上下文：摘要 → 主題筆記",
    "title": "摘要會遺失細節：從單一摘要壓縮到主題筆記",
    "problem": "舊版（v1）把舊歷史壓成單一摘要；長任務的精確細節在壓縮中流失，代理被迫重找證據。"
  },
  {
    "tab": "agent", "slug": "lsm-memory", "num": "08", "nav": "LSM 分層封存", "group": "上下文管理、壓縮與單任務長程",
    "kicker": "單任務長程抗膨脹演算法",
    "title": "LSM 分層封存：活頭有界，冷檔不可變",
    "problem": "單一任務跨天／跨週運行後，主題筆記與 SIM 帳本無限膨脹，最終超過輸出預算導致壓縮失敗。"
  },
  {
    "tab": "agent", "slug": "workflows", "num": "09", "nav": "PromptLoop FSM", "group": "編排、外部資料與參考",
    "kicker": "PromptLoop 確定性單代理狀態機（promptloop.py）",
    "title": "控制器管流程、每階段一隻新鮮 Agent、證據決定結案",
    "problem": "線性步驟無法回跳修正、共用長對話會球員兼裁判，小模型常自稱完成卻未通過客觀驗證。"
  },
  {
    "tab": "agent", "slug": "web", "num": "10", "nav": "網路研究", "group": "編排、外部資料與參考",
    "kicker": "外部與即時資料",
    "title": "網路資料以「步驟」取得，像文件一樣交付",
    "problem": "最新資料不在工作區；但網頁不可信、結果量大，查詢本身會離開本機。"
  },
  {
    "tab": "agent", "slug": "example", "num": "11", "nav": "完整範例", "group": "編排、外部資料與參考",
    "kicker": "串起整套方法",
    "title": "一份掃描發票，從檔案到可核對的回答",
    "problem": "各機制單獨看過於抽象；需一個案例展示資料如何依序通過各道邊界。"
  },
  {
    "tab": "agent", "slug": "reference", "num": "12", "nav": "實作索引", "group": "編排、外部資料與參考",
    "kicker": "從方法找到程式",
    "title": "責任索引與閱讀檢查表",
    "problem": "從方法定位到負責模組與測試，並避開常見概念混淆。"
  },

  // ==================== TAB 2: Breezeman ====================
  {
    "tab": "breezeman", "slug": "breezeman-architecture", "num": "B0", "nav": "系統架構與 FastAPI 層", "group": "宿主與併發模型",
    "kicker": "Breezeman 宿主總覽 · HTTP / WebSocket / 雙排程迴圈",
    "title": "單一宿主承載長程對話、排程、記憶與 Studio",
    "problem": "同步的 kentc_agent 無法直接處理長程常駐、多任務工作區隔離、即時串流與背景排程。"
  },
  {
    "tab": "breezeman", "slug": "breezeman-long-horizon", "num": "B1", "nav": "排程狀態機與長程韌性", "group": "長程排程與防呆",
    "kicker": "Breezeman 排程核心 · 非同步結算、熔斷與防漂移",
    "title": "非同步 Worker 結算、指數退避與防壓縮震盪",
    "problem": "排程只看同步派發會漏接 worker 故障、重試堆疊重複 prompt、固定提示過大引發每次強制壓縮，重啟會留下殭屍狀態。"
  },
  {
    "tab": "breezeman", "slug": "breezeman-memory", "num": "B2", "nav": "全域記憶與 Dreaming 蒸餾", "group": "跨會話長期記憶",
    "kicker": "Breezeman 離線蒸餾 · 三軌知識、BM25 檢索與 O(1) 快篩",
    "title": "O(1) 快篩、BM25 兩階段檢索與三軌冪等寫入",
    "problem": "跨月累積數百份 session 與上千條記憶後，全量掃描 .jsonl 與整份 INDEX.md 會拖垮磁碟與上下文視窗。"
  },
  {
    "tab": "breezeman", "slug": "studio", "num": "B3", "nav": "Folder-as-Studio 整合", "group": "結構化案件整合",
    "kicker": "Breezeman × Studio · 資料夾即應用",
    "title": "在 Breezeman 內掛載三頁結構化案件流程",
    "problem": "結構化審查需要嚴格 output/checks 與三頁非同步工作台，但另起獨立伺服器會割裂工作區與全域記憶。"
  }
];

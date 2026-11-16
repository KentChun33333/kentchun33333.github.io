// Topic list for the docs reader (index.html) and the standalone topic pages (topics/<slug>.html).
// Order is reading order. Keep num, kicker and title in step with each page's eyebrow and h2;
// `problem` is the one-line problem statement shown on the home page cards.
window.KENTC_TOPICS = [
  {
    "slug": "layers", "num": "00", "nav": "三種使用層", "group": "基礎：一個代理",
    "kicker": "同一個代理，三種使用層",
    "title": "越無人看管，權限越收斂",
    "problem": "同一代理服務三種場合：有人逐回合看管、無人看管的長流程、處理不可信上傳的網頁。單一權限組不是過寬就是過窄。"
  },
  {
    "slug": "principles", "num": "01", "nav": "方法論", "group": "基礎：一個代理",
    "kicker": "先理解方法，再看模組",
    "title": "把任務拆成「證據、行動、控制、紀錄」",
    "problem": "小模型會宣稱已完成卻未寫檔、心算出錯、把推論寫成原文；只看回覆無法核對。"
  },
  {
    "slug": "loop", "num": "02", "nav": "執行迴圈", "group": "基礎：一個代理",
    "kicker": "任務如何真的往前走",
    "title": "一次 run 可以包含多個 operation",
    "problem": "任務需數十次模型－工具往返；任一步可能截斷、無效或中斷，也可能用盡次數仍未作答。"
  },
  {
    "slug": "capabilities", "num": "03", "nav": "能力與策略", "group": "基礎：一個代理",
    "kicker": "誰決定上限，誰決定用法",
    "title": "伺服器能力 ≠ 代理設定",
    "problem": "各部署的視窗、影像能力、速率限制與連線行為不同；寫死數值或盲目重送會超限、重複或卡死。"
  },
  {
    "slug": "vertical", "num": "04", "nav": "上下文視窗", "group": "上下文視窗：長任務的核心限制",
    "kicker": "上下文視窗的兩個方向",
    "title": "跨回合壓縮歷史；單回合控制新資料",
    "problem": "W ≈ 6 萬 tokens，單件審查案原始資料 ≈ 一個視窗；歷史逐輪累積（縱向），單次結果可一次塞滿（橫向）。"
  },
  {
    "slug": "documents", "num": "05", "nav": "文件解析", "group": "上下文視窗：長任務的核心限制",
    "kicker": "橫向的極端：大型文件與影像",
    "title": "先轉換，再依預算解析；只接受完整結果",
    "problem": "單一 PDF、掃描檔或 Office 檔即可超過剩餘視窗；部分 PDF 只有佔位文字。直接注入不是放不下，就是讀錯。"
  },
  {
    "slug": "folders", "num": "06", "nav": "記憶分工", "group": "上下文視窗：長任務的核心限制",
    "kicker": "工作區與工作階段，不是長期記憶系統",
    "title": "「存在哪裡」與「模型看得到什麼」是兩個問題",
    "problem": "「記憶」被混指檔案、對話紀錄與目前上下文；混用導致誤以為存過即可見。"
  },
  {
    "slug": "eval", "num": "07", "nav": "長任務記憶：摘要 → 主題筆記", "group": "上下文視窗：長任務的核心限制",
    "kicker": "長任務的上下文：摘要 → 主題筆記",
    "title": "摘要會遺失細節：從單一摘要壓縮到主題筆記",
    "problem": "舊版（v1）把舊歷史壓成單一摘要；長任務的精確細節在壓縮中流失，代理被迫重找證據。"
  },
  {
    "slug": "workflows", "num": "08", "nav": "工作流程", "group": "編排與外部資料",
    "kicker": "用工作流程約束方法，不建立代理團隊",
    "title": "同一個 Agent，依階段改變指示與工具清單",
    "problem": "長任務需固定順序、人工審核與斷點續跑；單一大提示會漏步、權限不分、失敗即全部重來。"
  },
  {
    "slug": "web", "num": "09", "nav": "網路研究", "group": "編排與外部資料",
    "kicker": "外部與即時資料",
    "title": "網路資料以「步驟」取得，像文件一樣交付",
    "problem": "最新資料不在工作區；但網頁不可信、結果量大，查詢本身會離開本機。"
  },
  {
    "slug": "studio", "num": "10", "nav": "Studio 應用", "group": "應用與參考",
    "kicker": "Studio 應用框架",
    "title": "一個三頁非同步迴圈；換一份 YAML，就是新的應用",
    "problem": "分析師需可核對的結構化結果，輸入不可信；代理直接產生頁面不安全，逐情境複製前端不可維護。"
  },
  {
    "slug": "example", "num": "11", "nav": "完整範例", "group": "應用與參考",
    "kicker": "串起整套方法",
    "title": "一份掃描發票，從檔案到可核對的回答",
    "problem": "各機制單獨看過於抽象；需一個案例展示資料如何依序通過各道邊界。"
  },
  {
    "slug": "reference", "num": "12", "nav": "實作索引", "group": "應用與參考",
    "kicker": "從方法找到程式",
    "title": "責任索引與閱讀檢查表",
    "problem": "從方法定位到負責模組與測試，並避開常見概念混淆。"
  }
];

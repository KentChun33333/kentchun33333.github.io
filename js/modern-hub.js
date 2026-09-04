/**
 * AUTUMN MEMO // INTELLIGENCE NEXUS - CLIENT INTERACTIVE ENGINE
 * Author: Kent Chiu
 * Description: Real-time telemetry simulation, instant multi-layer search,
 * preview drawer controller, and skill contract inspector modal.
 */

(function () {
  'use strict';

  // --- Skills Data Dictionary ---
  const SKILLS_DATA = {
    'guarded-skill-evolution': {
      title: 'Guarded Skill Evolution (GSE)',
      category: 'Skill Evolution & Safety',
      badge: 'Frontier Agentic',
      description: 'Requirement-aware, regression-controlled approach to modifying persistent LLM agent skills using Pareto frontiers and failure attribution.',
      contract: {
        inputs: ['Source candidate skill', 'Regression test suite', 'Task contract constraints'],
        outputs: ['Verified skill version', 'Comparative Pareto evaluation report', 'Failure owner trace'],
        trigger: 'Triggered when an agent encounters novel task invalidations or requires skill mutation without regression.'
      },
      prompt: `Role: Skill Evolution Guard\nObjective: Evaluate proposed skill modifications against baseline test sets.\nRule 1: Reject any mutation that causes regression on frozen benchmark benchmarks.\nRule 2: Identify whether failure originates in environment drift or skill prompt flaw.\nRule 3: Produce comparative diff with verifiable test evidence.`,
      snippet: `python -m skills.guarded_skill_evolution.evaluate \\\n  --candidate ./skills/candidate_skill.md \\\n  --baseline ./skills/baseline_skill.md \\\n  --benchmark ./benchmarks/agent_eval_suite.json`
    },
    'build-async-agentic-web-demo': {
      title: 'Build Async Agentic Web Demo',
      category: 'Web & Systems Architecture',
      badge: 'Production Ready',
      description: 'Architect and build asynchronous agentic web demos with human-in-the-loop review, multi-stage pipelines, and event-driven simulations.',
      contract: {
        inputs: ['Agent workflow spec', 'Domain dataset (e.g. TER/AML, Wealth)', 'Interaction model'],
        outputs: ['Standalone zero-dependency HTML5 demo', 'Simulated packet network', 'Decision trace log'],
        trigger: 'Used when demonstrating multi-agent workflows with asynchronous queues and human review checkpoints.'
      },
      prompt: `System: Agentic Demo Architect\nDesign a 3-page interactive simulation:\n1. Intake & Evidence Upload (analyst context)\n2. Human Review & Correction (OCR/VLM confidence inspection)\n3. Report Generation & Human-Directed Refinement (live multi-agent reasoning trace)`,
      snippet: `npm run build:agent-demo -- --template=ter-banking-v15 --output=./dist/agent_demo.html`
    },
    'knowledge-distill': {
      title: 'Knowledge Distillation Engine',
      category: 'Reasoning & Knowledge',
      badge: 'Core Skill',
      description: 'Distill dense code repositories, research papers, and heterogeneous corpora into compact, traceable, evidence-grounded knowledge packages.',
      contract: {
        inputs: ['Raw repository / PDF paper collection', 'Task contract', 'Audience specification'],
        outputs: ['Normalized knowledge package', 'Dependency manifest', 'Invalidation criteria ledger'],
        trigger: 'Activated during deep research workflows where surface summaries fail and structural knowledge is needed.'
      },
      prompt: `Contract-first Knowledge Distiller:\nExtract operational flow first, terminology second, and boundaries always.\nEvery claim must bind directly to raw source file and line offsets.`,
      snippet: `python -m skills.knowledge_distill \\\n  --corpus ./raw_papers/ \\\n  --output ./distilled_pkg/ \\\n  --mode structured`
    },
    'semantic-pattern-mining': {
      title: 'Semantic Pattern Mining',
      category: 'Analytics & Discovery',
      badge: 'Algorithmic',
      description: 'Extract recurring semantic, causal, and sequential patterns from noisy, unstructured text using embedding clustering and contrastive auditing.',
      contract: {
        inputs: ['Unstructured logs/tickets/alerts', 'Schema definitions', 'Evaluation labels'],
        outputs: ['Canonical pattern cards', 'Support & Lift metrics', 'Adversarial counter-examples'],
        trigger: 'Applied when diagnosing systemic workflow faults, incident cascades, or algorithmic trading anomalies.'
      },
      prompt: `Analyze heterogeneous event stream:\n1. Normalize cases into canonical schema.\n2. Compute vector embeddings & cluster into semantic groups.\n3. Generate hypothesized causal pattern cards.\n4. Run contrastive audit against control baselines.`,
      snippet: `python -m skills.pattern_mining.mine \\\n  --input ./logs/system_events.jsonl \\\n  --min-support 0.05 \\\n  --min-lift 1.8`
    },
    'evaluate-web-deliverable': {
      title: 'Evaluate Web Deliverables',
      category: 'Evaluation & QA',
      badge: 'Auditing',
      description: 'Automated profile-based grading and verification of research sites, agentic demos, and system explainers against strict usability rubrics.',
      contract: {
        inputs: ['Target HTML artifact', 'Profile rules (research-site / system-demo / agentic-demo)'],
        outputs: ['Weighted scorecard (0-100)', 'Compliance checklist', 'Critical usability defects'],
        trigger: 'Executes before committing or releasing any generated web asset.'
      },
      prompt: `Audit deliverable against assigned profile:\n- Check evidence preservation and interactive claims.\n- Inspect responsive layout and accessibility.\n- Verify simulation stability under step-through testing.`,
      snippet: `node ./skills/evaluate-web-deliverable/runner.js \\\n  --file ./ai-research-insights/frontier-convergence.html \\\n  --profile research-site`
    },
    'evaluate-executive-resume': {
      title: 'Evaluate Executive Resume',
      category: 'Evaluation & QA',
      badge: 'Assessment',
      description: 'Multi-factor candidate assessment evaluating strategic scope, leadership footprint, quantifiable revenue impact, and execution rigor.',
      contract: {
        inputs: ['Candidate resume text', 'Target role profile & rubric'],
        outputs: ['Dimension scorecard', 'Risk flags', 'Executive briefing note'],
        trigger: 'Used in executive talent evaluation and organizational structuring.'
      },
      prompt: `Evaluate executive candidacy:\n1. Strategic Impact (P&L ownership, growth multipliers)\n2. Technical & Domain Mastery\n3. Leadership Scale\n4. Red-flag consistency and trajectory gaps.`,
      snippet: `python -m skills.evaluate_executive_resume --resume candidate.md --role vp_engineering`
    },
    'markdown-to-pdf': {
      title: 'Markdown to Print-Ready PDF',
      category: 'Publishing Tools',
      badge: 'Utility',
      description: 'Convert Markdown documents into clean, elegant, print-ready PDF files with automated A4 page-break safety and Playwright typography.',
      contract: {
        inputs: ['Markdown source file', 'Styling template CSS'],
        outputs: ['Vector print-ready PDF file', 'Rendering report'],
        trigger: 'Used for compiling whitepapers, resumes, and client advisory briefs.'
      },
      prompt: `Compile Markdown with Playwright:\n- Set margins: 12mm top/bottom, 15mm left/right\n- Ensure page-break-after: avoid on headers\n- Apply high-legibility Inter typeface.`,
      snippet: `python ./skills/markdown-to-pdf/convert.py \\\n  --input ./paper.md \\\n  --output ./paper.pdf \\\n  --style modern`
    },
    'ideogram-image-generation': {
      title: 'Ideogram Image Generation',
      category: 'Generative Media',
      badge: 'Visual AI',
      description: 'Generate high-fidelity local visuals and concept graphics with Ideogram 4 FP8 for portfolio headers and research illustrations.',
      contract: {
        inputs: ['Prompt specification', 'Aspect ratio', 'Style preset'],
        outputs: ['High-res generated image', 'Prompt metadata record'],
        trigger: 'Called to generate visual assets for blog posts and demo hero covers.'
      },
      prompt: `Ideogram 4 Prompt Generator:\nGenerate photo-realistic or architectural concept art with accurate text rendering, dark atmospheric lighting, and clean cyber-minimalist geometry.`,
      snippet: `python -m skills.ideogram.generate \\\n  --prompt "cybernetic multi-agent financial network, obsidian dark aesthetic, neon glowing edges" \\\n  --aspect 16:9`
    },
    'charting': {
      title: 'Quantitative Charting Library',
      category: 'Visualization',
      badge: 'Quant Tools',
      description: 'Quantitative visualization recipes for financial order books, cluster silhouette validation, macroeconomic radars, and model benchmarks.',
      contract: {
        inputs: ['Time series or matrix data', 'Chart specification type'],
        outputs: ['SVG / Canvas visualization component', 'Interactive legend & tooltip'],
        trigger: 'Used across all quant articles and private wealth dashboards.'
      },
      prompt: `Render quantitative visualization:\n- SVG-first vector curves with glowing stroke accents\n- High dynamic range color palette\n- Zero dependency browser execution.`,
      snippet: `python -m skills.charting.render --data ./data/order_book.csv --type order_depth`
    },
    'cross-evolve-skill': {
      title: 'Cross-Model Skill Evolution',
      category: 'Skill Evolution & Safety',
      badge: 'Experimental',
      description: 'Synthesizes and aligns skill capabilities across disparate LLM agents (Gemini, Claude, Qwen, DeepSeek) through contrastive self-play.',
      contract: {
        inputs: ['Agent skill definition', 'Disparate model runtime interfaces'],
        outputs: ['Cross-compatible skill markdown', 'Runtime translation adapters'],
        trigger: 'Used when migrating workflows between frontier model ecosystems.'
      },
      prompt: `Cross-Evolve Skill Protocol:\nTranslate skill operational harness across differing agent prompt specifications while preserving tool calling contracts.`,
      snippet: `python -m skills.cross_evolve --skill ./skills/web/SKILL.md --target-model claude_fable`
    },
    'web': {
      title: 'Source-Grounded Web Deliverables',
      category: 'Web & Systems Architecture',
      badge: 'Core Skill',
      description: 'Build source-grounded interactive HTML deliverables: research sites, system demos, and agentic workflow explainers.',
      contract: {
        inputs: ['Knowledge package', 'Task contract', 'Selected web category'],
        outputs: ['Offline-capable HTML5 artifact', 'Evidence linking map'],
        trigger: 'Default engine for generating all standalone interactive research papers in this hub.'
      },
      prompt: `Generate offline-capable interactive artifact:\nPreserve all evidence links, provide immediate feedback on interactions, and enforce aesthetic excellence.`,
      snippet: `python -m skills.web.build --contract ./task-config.json`
    }
  };

  // --- Real-Time Telemetry Simulation Data ---
  const LOG_TEMPLATES = [
    { type: 'info', text: '<b>[ROUTER]</b> Dispatched task #AGY-902 to <b>Gemini 3.8 Flash</b> (Parallel reasoning enabled).' },
    { type: 'success', text: '<b>[OCR-VLM]</b> Extracted 7 key-value pairs from customs invoice. Confidence: <b>96.8%</b>.' },
    { type: 'info', text: '<b>[MEMORY-RAG]</b> Clawdbot Hybrid Search hit: 18 chunks retrieved (BM25 + Cosine sim: 0.884).' },
    { type: 'warn', text: '<b>[RISK-AGENT]</b> Flagged sanction nexus on Counterparty #2 in private wealth portfolio WDI-0824.' },
    { type: 'success', text: '<b>[GSE-ENGINE]</b> Guarded skill evaluation passed 42/42 regression tests. Zero capability degradation.' },
    { type: 'info', text: '<b>[SYNC]</b> Synced knowledge base vector embeddings: 2,340 governed documents indexed.' },
    { type: 'info', text: '<b>[BENCHMARK]</b> Recorded <b>Claude Fable 5.1</b> reasoning latency: 280ms / 85 tok/s.' },
    { type: 'success', text: '<b>[DISPATCH]</b> Published Git commit via in-browser ZIP publisher. Status: <b>HTTP 201 Created</b>.' }
  ];

  let isTelemetryRunning = true;
  let telemetryInterval = null;

  function initTelemetry() {
    const streamLog = document.getElementById('streamLog');
    const playPauseBtn = document.getElementById('telemetryPlayPause');
    const clearBtn = document.getElementById('telemetryClear');
    const stepBtn = document.getElementById('telemetryStep');

    if (!streamLog) return;

    function addLogEntry(item) {
      const entry = document.createElement('div');
      entry.className = 'log-entry ' + (item.type || 'info');
      
      const now = new Date();
      const timeStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0').slice(0, 2);
      
      entry.innerHTML = `
        <span class="log-time">${timeStr}</span>
        <div class="log-msg">${item.text}</div>
      `;
      
      streamLog.insertBefore(entry, streamLog.firstChild);
      if (streamLog.children.length > 50) {
        streamLog.removeChild(streamLog.lastChild);
      }
    }

    function tick() {
      if (!isTelemetryRunning) return;
      const rand = LOG_TEMPLATES[Math.floor(Math.random() * LOG_TEMPLATES.length)];
      addLogEntry(rand);

      // Randomly update model latencies slightly for realism
      const latencies = document.querySelectorAll('.dynamic-latency');
      latencies.forEach(el => {
        const base = parseInt(el.dataset.base || '180', 10);
        const jitter = Math.floor((Math.random() - 0.5) * 24);
        el.textContent = `${Math.max(80, base + jitter)}ms`;
      });
    }

    telemetryInterval = setInterval(tick, 2800);

    if (playPauseBtn) {
      playPauseBtn.addEventListener('click', () => {
        isTelemetryRunning = !isTelemetryRunning;
        playPauseBtn.textContent = isTelemetryRunning ? '⏸ Pause Stream' : '▶ Resume Stream';
        playPauseBtn.classList.toggle('active', isTelemetryRunning);
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        streamLog.innerHTML = '';
        addLogEntry({ type: 'info', text: '<b>[SYSTEM]</b> Telemetry log cleared by operator.' });
      });
    }

    if (stepBtn) {
      stepBtn.addEventListener('click', () => {
        const rand = LOG_TEMPLATES[Math.floor(Math.random() * LOG_TEMPLATES.length)];
        addLogEntry(rand);
      });
    }
  }

  // --- Instant Search & Category Filtering ---
  function initSearchAndFilter() {
    const searchInput = document.getElementById('globalSearchInput');
    const filterPills = document.querySelectorAll('.filter-pill');
    const searchableItems = document.querySelectorAll('[data-search-item]');
    const pillCounts = {
      all: document.getElementById('countAll'),
      research: document.getElementById('countResearch'),
      demos: document.getElementById('countDemos'),
      blogs: document.getElementById('countBlogs'),
      skills: document.getElementById('countSkills'),
      monitoring: document.getElementById('countMonitoring')
    };

    let currentCategory = 'all';
    let currentQuery = '';

    function filterItems() {
      let visibleCounts = { all: 0, research: 0, demos: 0, blogs: 0, skills: 0, monitoring: 0 };

      searchableItems.forEach(item => {
        const itemCat = item.dataset.category || '';
        const itemText = (item.textContent || '').toLowerCase();
        const matchesCategory = (currentCategory === 'all') || (itemCat === currentCategory);
        const matchesQuery = !currentQuery || itemText.includes(currentQuery);

        if (matchesCategory && matchesQuery) {
          item.style.display = '';
          visibleCounts[itemCat] = (visibleCounts[itemCat] || 0) + 1;
          visibleCounts.all++;
        } else {
          item.style.display = 'none';
        }
      });

      // Update counters
      Object.keys(pillCounts).forEach(key => {
        if (pillCounts[key]) {
          pillCounts[key].textContent = visibleCounts[key] || 0;
        }
      });
    }

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        currentQuery = e.target.value.trim().toLowerCase();
        filterItems();
      });

      // Quick key shortcut (Cmd+K or /)
      window.addEventListener('keydown', (e) => {
        if ((e.key === '/' || (e.metaKey && e.key === 'k') || (e.ctrlKey && e.key === 'k')) && document.activeElement !== searchInput) {
          e.preventDefault();
          searchInput.focus();
          searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    }

    filterPills.forEach(pill => {
      pill.addEventListener('click', () => {
        filterPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentCategory = pill.dataset.filter || 'all';
        filterItems();
      });
    });

    // Initial count
    filterItems();
  }

  // --- Slide-in Live Preview Drawer ---
  function initPreviewDrawer() {
    const backdrop = document.getElementById('previewBackdrop');
    const drawer = document.getElementById('previewDrawer');
    const iframe = document.getElementById('drawerIframe');
    const drawerTitle = document.getElementById('drawerTitle');
    const drawerSubtitle = document.getElementById('drawerSubtitle');
    const drawerFullscreen = document.getElementById('drawerFullscreen');
    const drawerClose = document.getElementById('drawerClose');

    if (!drawer || !iframe) return;

    function openPreview(url, title, subtitle) {
      drawerTitle.textContent = title || 'Interactive Asset Preview';
      drawerSubtitle.textContent = subtitle || url;
      drawerFullscreen.href = url;
      iframe.src = url;
      backdrop.classList.add('open');
      drawer.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closePreview() {
      backdrop.classList.remove('open');
      drawer.classList.remove('open');
      iframe.src = 'about:blank';
      document.body.style.overflow = '';
    }

    // Attach to all preview trigger buttons
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-preview-url]');
      if (btn) {
        e.preventDefault();
        const url = btn.dataset.previewUrl;
        const title = btn.dataset.previewTitle || 'Live Preview';
        const subtitle = btn.dataset.previewSubtitle || url;
        openPreview(url, title, subtitle);
      }
    });

    if (drawerClose) drawerClose.addEventListener('click', closePreview);
    if (backdrop) backdrop.addEventListener('click', closePreview);

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawer.classList.contains('open')) {
        closePreview();
      }
    });
  }

  // --- Interactive Skill Inspector Modal ---
  function initSkillModal() {
    const modalBackdrop = document.getElementById('skillModalBackdrop');
    const modalTitle = document.getElementById('skillModalTitle');
    const modalSubtitle = document.getElementById('skillModalSubtitle');
    const modalOverview = document.getElementById('skillModalOverview');
    const modalPrompt = document.getElementById('skillModalPrompt');
    const modalSnippet = document.getElementById('skillModalSnippet');
    const modalClose = document.getElementById('skillModalClose');
    const copyBtn = document.getElementById('skillCopyPrompt');

    if (!modalBackdrop) return;

    const tabs = document.querySelectorAll('.modal-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const targetTab = tab.dataset.tab;

        document.querySelectorAll('.modal-tab-content').forEach(c => c.style.display = 'none');
        const targetContent = document.getElementById('tabContent-' + targetTab);
        if (targetContent) targetContent.style.display = 'block';
      });
    });

    function openSkillModal(skillId) {
      const data = SKILLS_DATA[skillId];
      if (!data) return;

      modalTitle.textContent = data.title;
      modalSubtitle.textContent = `CATEGORY: ${data.category.toUpperCase()} · [${data.badge}]`;
      
      modalOverview.innerHTML = `
        <p style="margin-bottom: 16px; font-size: 15px; color: #f1f5f9;">${data.description}</p>
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px; margin-bottom: 14px;">
          <b style="color: #10b981; font-family: var(--font-mono); font-size: 11px; display: block; margin-bottom: 6px;">TASK TRIGGER CONDITION</b>
          <div style="font-size: 13px; color: #cbd5e1;">${data.contract.trigger}</div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px;">
            <b style="color: #38bdf8; font-family: var(--font-mono); font-size: 10px; display: block; margin-bottom: 6px;">REQUIRED INPUT CONTRACT</b>
            <ul style="padding-left: 16px; font-size: 12px; color: #94a3b8;">
              ${data.contract.inputs.map(i => `<li>${i}</li>`).join('')}
            </ul>
          </div>
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px;">
            <b style="color: #f59e0b; font-family: var(--font-mono); font-size: 10px; display: block; margin-bottom: 6px;">DELIVERABLE OUTPUT CONTRACT</b>
            <ul style="padding-left: 16px; font-size: 12px; color: #94a3b8;">
              ${data.contract.outputs.map(o => `<li>${o}</li>`).join('')}
            </ul>
          </div>
        </div>
      `;

      modalPrompt.textContent = data.prompt;
      modalSnippet.textContent = data.snippet;

      // Reset to overview tab
      tabs[0].click();

      modalBackdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeSkillModal() {
      modalBackdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    document.addEventListener('click', (e) => {
      const card = e.target.closest('[data-skill-id]');
      if (card) {
        e.preventDefault();
        openSkillModal(card.dataset.skillId);
      }
    });

    if (modalClose) modalClose.addEventListener('click', closeSkillModal);
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', (e) => {
        if (e.target === modalBackdrop) closeSkillModal();
      });
    }

    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        const text = modalPrompt.textContent;
        navigator.clipboard.writeText(text).then(() => {
          const originalText = copyBtn.textContent;
          copyBtn.textContent = '✓ Copied!';
          setTimeout(() => { copyBtn.textContent = originalText; }, 1800);
        });
      });
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modalBackdrop.classList.contains('open')) {
        closeSkillModal();
      }
    });
  }

  // --- Smooth Active Nav Scroll Spy ---
  function initScrollSpy() {
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    const sections = Array.from(navLinks).map(link => {
      const id = link.getAttribute('href').slice(1);
      return document.getElementById(id);
    }).filter(Boolean);

    window.addEventListener('scroll', () => {
      const scrollPos = window.scrollY + 120;
      let currentSection = null;

      sections.forEach(sec => {
        if (sec.offsetTop <= scrollPos && (sec.offsetTop + sec.offsetHeight) > scrollPos) {
          currentSection = sec;
        }
      });

      if (currentSection) {
        navLinks.forEach(link => {
          link.classList.toggle('active', link.getAttribute('href') === `#${currentSection.id}`);
        });
      }
    });
  }

  // DOM Ready
  document.addEventListener('DOMContentLoaded', () => {
    initTelemetry();
    initSearchAndFilter();
    initPreviewDrawer();
    initSkillModal();
    initScrollSpy();
  });

})();

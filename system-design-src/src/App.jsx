import { useCallback, useEffect, useMemo, useState } from 'react';
import Scene, { FLOW_COLORS, lessonViewBox } from './Scene.jsx';
import { lessons } from './lessons.js';

function parseHash() {
  const [, id, s] = window.location.hash.match(/^#\/([\w-]+)(?:\/(\d+))?/) ?? [];
  const li = Math.max(0, lessons.findIndex((l) => l.id === id));
  const lesson = lessons[li];
  const si = Math.min(Math.max(0, (Number(s) || 1) - 1), lesson.steps.length - 1);
  return { li, si };
}

const PROGRESS_KEY = 'sd-progress';
const loadProgress = () => {
  try {
    return JSON.parse(localStorage.getItem(PROGRESS_KEY)) ?? {};
  } catch {
    return {};
  }
};

export default function App() {
  const [{ li, si }, setPos] = useState(parseHash);
  const [progress, setProgress] = useState(loadProgress);
  const [menuOpen, setMenuOpen] = useState(false);

  const lesson = lessons[li];
  const step = lesson.steps[si];
  const viewBox = useMemo(() => lessonViewBox(lesson), [lesson]);
  const isLast = si === lesson.steps.length - 1;

  const go = useCallback((nli, nsi) => {
    window.location.hash = `#/${lessons[nli].id}/${nsi + 1}`;
  }, []);

  useEffect(() => {
    const onHash = () => setPos(parseHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Remember the furthest step reached per lesson.
  useEffect(() => {
    setProgress((p) => {
      if ((p[lesson.id] ?? 0) >= si + 1) return p;
      const next = { ...p, [lesson.id]: si + 1 };
      localStorage.setItem(PROGRESS_KEY, JSON.stringify(next));
      return next;
    });
  }, [lesson.id, si]);

  const next = useCallback(() => {
    if (!isLast) go(li, si + 1);
    else if (li < lessons.length - 1) go(li + 1, 0);
  }, [go, li, si, isLast]);
  const prev = useCallback(() => {
    if (si > 0) go(li, si - 1);
    else if (li > 0) go(li - 1, lessons[li - 1].steps.length - 1);
  }, [go, li, si]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'ArrowRight' || e.key === 'l') next();
      if (e.key === 'ArrowLeft' || e.key === 'h') prev();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [next, prev]);

  useEffect(() => {
    document.title = `${lesson.title} · System Design, Step by Step`;
  }, [lesson]);

  const usedFlows = [...new Set((step.flows ?? []).map((f) => f.type ?? 'req'))];

  return (
    <div className="app">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark" aria-hidden>◆</span>
          <div>
            <div className="brand-title">System Design</div>
            <div className="brand-sub">step by step</div>
          </div>
        </div>
        <nav>
          {lessons.map((l, i) => {
            const done = progress[l.id] ?? 0;
            return (
              <button
                key={l.id}
                className={`lesson-link ${i === li ? 'active' : ''}`}
                onClick={() => {
                  go(i, 0);
                  setMenuOpen(false);
                }}
              >
                <span className="lesson-num">{String(i + 1).padStart(2, '0')}</span>
                <span className="lesson-name">
                  {l.title}
                  <span className="lesson-meter">
                    <span style={{ width: `${(done / l.steps.length) * 100}%` }} />
                  </span>
                </span>
              </button>
            );
          })}
        </nav>
        <p className="sidebar-foot">Keys: ← / → to step</p>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="menu-btn" onClick={() => setMenuOpen((o) => !o)} aria-label="Lessons">
            ☰
          </button>
          <div>
            <div className="eyebrow">
              Lesson {li + 1} of {lessons.length}
            </div>
            <h1>{lesson.title}</h1>
          </div>
        </header>

        <section className="stage">
          <Scene step={step} stepKey={`${lesson.id}-${si}`} viewBox={viewBox} />
          {step.stats && (
            <div className="stats">
              {step.stats.map(([k, v, tone]) => (
                <div key={k} className={`stat ${tone ? `stat-${tone}` : ''}`}>
                  <span className="stat-k">{k}</span>
                  <span className="stat-v">{v}</span>
                </div>
              ))}
            </div>
          )}
          {usedFlows.length > 0 && (
            <div className="legend">
              {usedFlows.map((t) => (
                <span key={t}>
                  <i style={{ background: FLOW_COLORS[t].color }} />
                  {FLOW_COLORS[t].label}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="caption" key={`${lesson.id}-${si}`}>
          <div className="caption-head">
            <span className="step-count">
              {si + 1} / {lesson.steps.length}
            </span>
            <h2>{step.title}</h2>
          </div>
          {step.body.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          {step.takeaway && <p className="takeaway">{step.takeaway}</p>}
        </section>

        <footer className="controls">
          <button className="btn" onClick={prev} disabled={li === 0 && si === 0}>
            ← Back
          </button>
          <div className="dots">
            {lesson.steps.map((s, i) => (
              <button key={i} className={`dot ${i === si ? 'on' : ''} ${i < si ? 'past' : ''}`} onClick={() => go(li, i)} aria-label={`Step ${i + 1}: ${s.title}`} />
            ))}
          </div>
          <button className="btn btn-primary" onClick={next} disabled={isLast && li === lessons.length - 1}>
            {isLast && li < lessons.length - 1 ? 'Next lesson →' : 'Next →'}
          </button>
        </footer>
      </main>
    </div>
  );
}

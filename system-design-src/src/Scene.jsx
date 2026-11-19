import { useMemo } from 'react';

// 2:1 isometric projection. Grid (x, y) → screen; z lifts straight up.
const TW = 112;
const TH = 56;
const iso = (x, y, z = 0) => [((x - y) * TW) / 2, ((x + y) * TH) / 2 - z];

const PALETTE = {
  server: ['#a9c6f0', '#6f97d6', '#4b74b8'],
  lb: ['#f6d08f', '#e6ab5a', '#c98a35'],
  db: ['#cbb8ec', '#9a82d2', '#7660b3'],
  cache: ['#f6b0a3', '#e07f6f', '#c15f50'],
  queue: ['#f3d9a8', '#ddb470', '#bf934e'],
  worker: ['#b5e0bc', '#79c288', '#55a166'],
  cdn: ['#a8e0dc', '#62bcb7', '#439995'],
  service: ['#dcd3c5', '#b8ac9a', '#968a78'],
  client: ['#eadfce', '#d6c6af', '#bfae95'],
};

const HEIGHT = { server: 46, lb: 22, db: 44, cache: 26, queue: 12, worker: 34, cdn: 30, service: 38, client: 5 };

export const FLOW_COLORS = {
  req: { color: '#2f6fde', label: 'Request' },
  res: { color: '#2e9b5f', label: 'Response' },
  err: { color: '#d64545', label: 'Failure' },
  data: { color: '#8a5cd6', label: 'Data sync' },
  msg: { color: '#e0912f', label: 'Message / write' },
  ping: { color: '#7d8a99', label: 'Health check' },
};

const PACKET_Z = 14;

function Box({ kind, w, h }) {
  const [top, left, right] = PALETTE[kind];
  const hw = (TW / 2) * w;
  const hh = (TH / 2) * w;
  const pts = (arr) => arr.map((p) => p.join(',')).join(' ');
  return (
    <g>
      <polygon points={pts([[-hw, -h], [0, -h + hh], [0, hh], [-hw, 0]])} fill={left} />
      <polygon points={pts([[hw, -h], [0, -h + hh], [0, hh], [hw, 0]])} fill={right} />
      <polygon points={pts([[0, -h - hh], [hw, -h], [0, -h + hh], [-hw, -h]])} fill={top} />
    </g>
  );
}

function Cylinder({ kind, w, h }) {
  const [top, left, right] = PALETTE[kind];
  const rx = (TW / 2) * w * 0.85;
  const ry = (TH / 2) * w * 0.85;
  const ring = (y) => `M ${-rx} ${y} A ${rx} ${ry} 0 0 0 ${rx} ${y}`;
  return (
    <g>
      <path d={`M ${-rx} ${-h} L ${-rx} 0 A ${rx} ${ry} 0 0 0 ${rx} 0 L ${rx} ${-h} Z`} fill={`url(#grad-${kind})`} />
      <path d={ring(-h / 3)} fill="none" stroke={right} strokeWidth="1.5" opacity="0.7" />
      <path d={ring((-2 * h) / 3)} fill="none" stroke={right} strokeWidth="1.5" opacity="0.7" />
      <ellipse cx="0" cy={-h} rx={rx} ry={ry} fill={top} />
      <ellipse cx="0" cy={-h} rx={rx * 0.55} ry={ry * 0.55} fill={left} opacity="0.35" />
    </g>
  );
}

function Person({ x, y, color }) {
  return (
    <g transform={`translate(${x},${y})`}>
      <path d="M -7 0 Q -7 -14 0 -14 Q 7 -14 7 0 Z" fill={color} />
      <circle cx="0" cy="-19" r="5" fill={color} />
    </g>
  );
}

function Clients({ w }) {
  return (
    <g>
      <Box kind="client" w={w} h={HEIGHT.client} />
      <Person x={-14} y={-4} color="#5d6b7d" />
      <Person x={14} y={-4} color="#c77d4f" />
      <Person x={0} y={6} color="#3f7f6a" />
    </g>
  );
}

function QueueBody({ w, depth = 0 }) {
  const h = HEIGHT.queue;
  const cubes = Math.min(depth, 8);
  // Messages sit along the queue's long axis as small cubes.
  const items = [];
  for (let i = 0; i < cubes; i++) {
    const t = (i - (cubes - 1) / 2) * 0.16;
    const [cx, cy] = [(t * TW) / 2, (t * TH) / 2];
    items.push(
      <g key={i} transform={`translate(${cx},${cy - h})`}>
        <g className="pop">
          <Box kind="msgCube" w={0.13} h={10} />
        </g>
      </g>,
    );
  }
  return (
    <g>
      <Box kind="queue" w={w} h={h} />
      {items}
    </g>
  );
}
PALETTE.msgCube = ['#ffd27a', '#f0a73d', '#d18a25'];

function NodeShape({ node }) {
  const w = 0.62 * (node.scale ?? 1);
  const h = (HEIGHT[node.kind] ?? 36) * (node.scale ?? 1);
  switch (node.kind) {
    case 'client':
      return <Clients w={0.9 * (node.scale ?? 1)} />;
    case 'db':
      return <Cylinder kind="db" w={w} h={h} />;
    case 'queue':
      return <QueueBody w={0.9 * (node.scale ?? 1)} depth={node.depth} />;
    default:
      return (
        <g>
          <Box kind={node.kind} w={w} h={h} />
          {(node.kind === 'server' || node.kind === 'worker') && (
            <g opacity="0.55">
              {[0.3, 0.55, 0.8].map((f) => (
                <line key={f} x1={(-TW / 2) * w * 0.8} y1={-h * f + 2} x2={(-TW / 2) * w * 0.2} y2={-h * f + 2 + (TH / 2) * w * 0.6} stroke="#fff" strokeWidth="2" strokeLinecap="round" />
              ))}
            </g>
          )}
        </g>
      );
  }
}

function nodeTop(node) {
  const s = node.scale ?? 1;
  if (node.kind === 'client') return 48;
  const h = (HEIGHT[node.kind] ?? 36) * s;
  return h + (TH / 2) * 0.62 * s + (node.kind === 'queue' ? 14 : 0);
}

function Node({ node }) {
  const [sx, sy] = iso(node.x, node.y);
  const top = nodeTop(node);
  const cls = ['node', node.state && `node-${node.state}`].filter(Boolean).join(' ');
  return (
    <g className="node-pos" style={{ transform: `translate(${sx}px, ${sy}px)` }}>
      <g className={cls}>
        {node.state === 'hot' && <ellipse className="hot-glow" cx="0" cy="4" rx="58" ry="29" />}
        {node.state === 'focus' && <ellipse className="focus-ring" cx="0" cy="4" rx="54" ry="27" />}
        <NodeShape node={node} />
        {node.state === 'down' && (
          <g transform={`translate(0, ${-top / 2})`}>
            <g className="down-x">
              <circle r="13" fill="#d64545" />
              <path d="M -5 -5 L 5 5 M 5 -5 L -5 5" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
            </g>
          </g>
        )}
        <text className="node-label" y={(TH / 2) * 0.62 * (node.scale ?? 1) + 20}>
          {node.label}
        </text>
        {node.sub && (
          <text className="node-sub" y={(TH / 2) * 0.62 * (node.scale ?? 1) + 35}>
            {node.sub}
          </text>
        )}
        {node.badge && <Badge text={node.badge} y={-top - 16} tone={node.badgeTone ?? (node.state === 'down' || node.state === 'hot' ? 'bad' : 'info')} />}
      </g>
    </g>
  );
}

function Badge({ text, y, tone }) {
  const width = text.length * 7 + 18;
  return (
    <g transform={`translate(0, ${y})`}>
      <g className={`badge badge-${tone}`}>
        <rect x={-width / 2} y="-11" width={width} height="22" rx="11" />
        <text y="4">{text}</text>
      </g>
    </g>
  );
}

function routePoints(route, byId) {
  return route.map((id) => {
    const n = byId[id];
    if (!n) throw new Error(`Unknown node in route: ${id}`);
    return iso(n.x, n.y, PACKET_Z);
  });
}

function Flow({ flow, byId, uid }) {
  const pts = routePoints(flow.route, byId);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'} ${p[0]} ${p[1]}`).join(' ');
  let len = 0;
  for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  const dur = flow.dur ?? Math.max(1.2, len / (flow.speed ?? 150));
  const n = flow.n ?? 1;
  const color = FLOW_COLORS[flow.type ?? 'req'].color;
  const packets = [];
  for (let i = 0; i < n; i++) {
    const phase = ((flow.offset ?? 0) + i / n) * dur;
    packets.push(
      <g key={`${uid}-${i}`}>
        {flow.type === 'ping' ? (
          <circle r="3.5" fill={color} opacity="0.9" />
        ) : (
          <circle r="5.5" fill={color} stroke="#fff" strokeWidth="2" />
        )}
        <animateMotion dur={`${dur}s`} repeatCount="indefinite" begin={`${-phase}s`} path={d} calcMode="linear" />
      </g>,
    );
  }
  return <g className="flow">{packets}</g>;
}

function edgeKey(a, b) {
  return a < b ? `${a}|${b}` : `${b}|${a}`;
}

/** Fixed camera per lesson: union of every node position across all steps. */
export function lessonViewBox(lesson) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const step of lesson.steps) {
    for (const n of step.nodes) {
      const [sx, sy] = iso(n.x, n.y);
      minX = Math.min(minX, sx);
      maxX = Math.max(maxX, sx);
      minY = Math.min(minY, sy);
      maxY = Math.max(maxY, sy);
    }
  }
  const padX = 110;
  const top = 120;
  const bottom = 70;
  return [minX - padX, minY - top, maxX - minX + padX * 2, maxY - minY + top + bottom];
}

export default function Scene({ step, stepKey, viewBox }) {
  const byId = useMemo(() => Object.fromEntries(step.nodes.map((n) => [n.id, n])), [step]);

  const edges = useMemo(() => {
    const map = new Map();
    for (const l of step.links ?? []) map.set(edgeKey(l[0], l[1]), { a: l[0], b: l[1], style: l[2] ?? 'solid' });
    for (const f of step.flows ?? []) {
      for (let i = 1; i < f.route.length; i++) {
        const k = edgeKey(f.route[i - 1], f.route[i]);
        if (!map.has(k)) map.set(k, { a: f.route[i - 1], b: f.route[i], style: f.type === 'data' ? 'dashed' : 'solid' });
      }
    }
    return [...map.values()];
  }, [step]);

  const sorted = useMemo(() => [...step.nodes].sort((a, b) => a.x + a.y - (b.x + b.y)), [step]);

  return (
    <svg className="scene" viewBox={viewBox.join(' ')} preserveAspectRatio="xMidYMid meet" role="img" aria-label={step.title}>
      <defs>
        {Object.entries(PALETTE).map(([k, [, l, r]]) => (
          <linearGradient key={k} id={`grad-${k}`} x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor={l} />
            <stop offset="0.5" stopColor={l} />
            <stop offset="0.5" stopColor={r} />
            <stop offset="1" stopColor={r} />
          </linearGradient>
        ))}
        <pattern id="grid" width={TW} height={TH} patternUnits="userSpaceOnUse">
          <path d={`M 0 ${TH / 2} L ${TW / 2} 0 L ${TW} ${TH / 2} L ${TW / 2} ${TH} Z`} fill="none" stroke="#e6d8c5" strokeWidth="1" />
        </pattern>
      </defs>
      <rect x={viewBox[0] - 2000} y={viewBox[1] - 2000} width={viewBox[2] + 4000} height={viewBox[3] + 4000} fill="url(#grid)" opacity="0.7" />
      <g className="edges">
        {edges.map((e) => {
          const A = byId[e.a];
          const B = byId[e.b];
          if (!A || !B) return null;
          const [x1, y1] = iso(A.x, A.y, PACKET_Z);
          const [x2, y2] = iso(B.x, B.y, PACKET_Z);
          return <line key={`${e.a}-${e.b}`} x1={x1} y1={y1} x2={x2} y2={y2} className={`edge edge-${e.style}`} />;
        })}
      </g>
      <g className="nodes">
        {sorted.map((n) => (
          <Node key={n.id} node={n} />
        ))}
      </g>
      <g className="flows" key={stepKey}>
        {(step.flows ?? []).map((f, i) => (
          <Flow key={i} flow={f} byId={byId} uid={`${stepKey}-${i}`} />
        ))}
      </g>
    </svg>
  );
}

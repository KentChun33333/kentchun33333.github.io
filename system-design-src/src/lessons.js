// Lesson content. Each step is a complete scene:
//   nodes: { id, kind, x, y, label, sub?, state?: 'hot'|'down'|'dim'|'focus', badge?, badgeTone?, scale?, depth? }
//   flows: { route: [nodeId...], type?: 'req'|'res'|'err'|'data'|'msg'|'ping', n?, offset?, dur?, speed? }
//   links: [[a, b, 'solid'|'dashed']] for static connections without traffic
//   stats: [[label, value, tone?]]
// Node kinds: client, server, lb, db, cache, queue, worker, cdn, service.

const N = (id, kind, x, y, label, extra = {}) => ({ id, kind, x, y, label, ...extra });
const F = (route, extra = {}) => ({ route, ...extra });

const scaling = {
  id: 'scaling',
  title: 'From one server to many',
  steps: [
    {
      title: 'Everything on one machine',
      nodes: [N('users', 'client', 0, 0, 'Users', { sub: '~100 / day' }), N('app', 'server', 3, 0, 'Server', { sub: 'web + app + database' })],
      flows: [F(['users', 'app'], { n: 2 }), F(['app', 'users'], { type: 'res', n: 2, offset: 0.25 })],
      stats: [['Users', '100'], ['p95 latency', '80 ms', 'good'], ['Monthly cost', '$20']],
      body: [
        'Nearly every product starts out like this: one machine runs the web server, the application code and the database. A request comes in, the code reads or writes some rows, and a response goes back.',
        'This is the right place to start. It is cheap, a single person can understand all of it, and deploying means copying files to one box.',
      ],
      takeaway: 'Don’t design for a million users on day one. Know what you will change when growth arrives.',
    },
    {
      title: 'Traffic grows',
      nodes: [N('users', 'client', 0, 0, 'Users', { sub: '10,000 / day', scale: 1.15 }), N('app', 'server', 3, 0, 'Server', { sub: 'web + app + database', state: 'hot', badge: 'CPU 97%' })],
      flows: [F(['users', 'app'], { n: 6 }), F(['app', 'users'], { type: 'res', n: 3, offset: 0.1 }), F(['app', 'users'], { type: 'err', n: 1, offset: 0.6 })],
      stats: [['Users', '10k'], ['p95 latency', '2.4 s', 'bad'], ['Errors', '3%', 'bad']],
      body: [
        'Usage grows. CPU, memory and disk are now shared by the app and the database, and they compete with each other. Requests start queuing, latency climbs, and some requests time out.',
        'Before you change the architecture, measure. Find out which resource is maxed out: CPU, memory, disk I/O or the network. The answer tells you what to fix.',
      ],
    },
    {
      title: 'Scale up: buy a bigger box',
      nodes: [N('users', 'client', 0, 0, 'Users', { sub: '10,000 / day', scale: 1.15 }), N('app', 'server', 3, 0, 'Bigger server', { sub: '64 cores · 256 GB', scale: 1.35, badge: 'CPU 35%', badgeTone: 'good' })],
      flows: [F(['users', 'app'], { n: 6 }), F(['app', 'users'], { type: 'res', n: 6, offset: 0.1 })],
      stats: [['p95 latency', '90 ms', 'good'], ['Monthly cost', '$900'], ['Code changes', 'none', 'good']],
      body: [
        'Vertical scaling means moving to a machine with more CPU, RAM or faster disks. You change no code, and it often buys a surprising amount of headroom.',
        'It has two hard limits. Machines only come so big, and price rises faster than capacity near the top end. You also still have one machine.',
      ],
      takeaway: 'Vertical scaling is a great first move. It just can’t be the only one.',
    },
    {
      title: 'One machine is one point of failure',
      nodes: [N('users', 'client', 0, 0, 'Users', { sub: '10,000 / day', scale: 1.15 }), N('app', 'server', 3, 0, 'Bigger server', { sub: 'kernel update, reboot…', scale: 1.35, state: 'down', badge: 'UNREACHABLE' })],
      flows: [F(['users', 'app'], { n: 4 }), F(['app', 'users'], { type: 'err', n: 4, offset: 0.15 })],
      stats: [['Availability', '0%', 'bad'], ['Downtime', 'every deploy', 'bad']],
      body: [
        'Hardware fails, operating systems need patches, and deploys need restarts. With a single server, each of those events takes the whole product offline.',
        'A component whose failure brings the whole system down is called a single point of failure (SPOF). Most of scaling comes down to removing them one at a time.',
      ],
    },
    {
      title: 'Separate the database',
      nodes: [N('users', 'client', 0, 0, 'Users'), N('app', 'server', 3, 0, 'App server', { sub: 'stateless code' }), N('db', 'db', 6, 0, 'Database', { sub: 'its own machine', state: 'focus' })],
      flows: [F(['users', 'app', 'db'], { n: 3 }), F(['db', 'app', 'users'], { type: 'res', n: 3, offset: 0.2 })],
      stats: [['Tiers', '2'], ['p95 latency', '70 ms', 'good']],
      body: [
        'The first structural split moves the database onto its own machine. The two tiers stop fighting over memory and disk, and you can size each one for its own job: lots of CPU for the app, fast disks and RAM for the database.',
        'Once the database lives elsewhere, the app server keeps no important data on local disk. It becomes stateless, so you can throw it away and replace it at any time.',
      ],
    },
    {
      title: 'Scale out: add more app servers',
      nodes: [
        N('users', 'client', 0, 0, 'Users', { sub: '1,000,000 / day', scale: 1.2 }),
        N('lb', 'lb', 2, 0, 'Load balancer', { state: 'focus' }),
        N('a1', 'server', 4.8, -1.5, 'App 1'),
        N('a2', 'server', 4.8, 0, 'App 2'),
        N('a3', 'server', 4.8, 1.5, 'App 3'),
        N('db', 'db', 7.2, 0, 'Database'),
      ],
      flows: [
        F(['users', 'lb', 'a1', 'db'], { dur: 2.4, offset: 0 }),
        F(['users', 'lb', 'a2', 'db'], { dur: 2.4, offset: 0.33 }),
        F(['users', 'lb', 'a3', 'db'], { dur: 2.4, offset: 0.66 }),
      ],
      stats: [['App servers', '3'], ['Survives', '1 server lost', 'good']],
      body: [
        'Horizontal scaling means adding more machines instead of bigger ones. Because the app servers are stateless, any one of them can serve any request. A load balancer sits in front, spreads traffic across them, and stops sending to any server that dies.',
        'Capacity now grows by adding boxes, and losing one server is no longer an outage. The next lessons look at the pieces that make this work: load balancers, caches, database scaling and queues.',
      ],
      takeaway: 'Stateless servers behind a load balancer: the basic pattern for scaling a web app.',
    },
  ],
};

const lbNodes = (extra = {}) => [
  N('users', 'client', 0, 0, 'Users', { scale: 1.15 }),
  N('lb', 'lb', 2.2, 0, 'Load balancer', extra.lb),
  N('s1', 'server', 5.2, -1.5, 'Server 1', extra.s1),
  N('s2', 'server', 5.2, 0, 'Server 2', extra.s2),
  N('s3', 'server', 5.2, 1.5, 'Server 3', extra.s3),
];

const loadBalancing = {
  id: 'load-balancing',
  title: 'Load balancing',
  steps: [
    {
      title: 'One front door, many servers',
      nodes: lbNodes({ lb: { state: 'focus', sub: 'one public address' } }),
      flows: [
        F(['users', 'lb', 's1'], { dur: 2.1, offset: 0 }),
        F(['users', 'lb', 's2'], { dur: 2.1, offset: 1 / 3 }),
        F(['users', 'lb', 's3'], { dur: 2.1, offset: 2 / 3 }),
      ],
      stats: [['Algorithm', 'round robin']],
      body: [
        'Clients only know one address, the load balancer’s. It accepts each connection and forwards it to one of the servers behind it, which are often called the pool or the backends.',
        'The simplest policy is round robin: server 1, then 2, then 3, then back to 1. Follow the packets and you will see them take turns.',
        'Load balancers work at one of two layers. A Layer 4 balancer forwards TCP connections without looking inside them. A Layer 7 balancer reads the HTTP request, so it can route by path, header or cookie, at the cost of more work per request.',
      ],
    },
    {
      title: 'Smarter choices: least connections',
      nodes: lbNodes({
        s1: { badge: '14 active', badgeTone: 'warn', sub: 'slow report queries' },
        s2: { badge: '3 active', badgeTone: 'good' },
        s3: { badge: '4 active', badgeTone: 'good' },
      }),
      flows: [
        F(['users', 'lb', 's2'], { n: 2, dur: 2.1 }),
        F(['users', 'lb', 's3'], { n: 2, dur: 2.1, offset: 0.25 }),
        F(['s1', 'lb'], { type: 'res', dur: 3.5 }),
      ],
      stats: [['Algorithm', 'least connections']],
      body: [
        'Round robin assumes every request costs about the same. In reality one server might be busy with a few slow report queries while the others sit idle.',
        'Least connections sends each new request to the server with the fewest requests in flight. Weighted variants give bigger machines a larger share. Hash-based routing (for example on user ID) sends the same client to the same server every time, which helps when servers keep a local cache.',
      ],
    },
    {
      title: 'Health checks',
      nodes: lbNodes({ s1: { badge: '200 OK', badgeTone: 'good' }, s2: { badge: '200 OK', badgeTone: 'good' }, s3: { badge: '200 OK', badgeTone: 'good' } }),
      flows: [
        F(['lb', 's1'], { type: 'ping', dur: 1.4 }),
        F(['lb', 's2'], { type: 'ping', dur: 1.4, offset: 0.2 }),
        F(['lb', 's3'], { type: 'ping', dur: 1.4, offset: 0.4 }),
      ],
      stats: [['Check', 'GET /health'], ['Every', '5 s'], ['Unhealthy after', '3 fails']],
      body: [
        'The load balancer regularly probes each backend, typically with a lightweight request to an endpoint such as /health. A server that fails several probes in a row is taken out of the rotation. Once it passes again, it is put back in.',
        'A good health check tests what actually matters: can this server reach its database, and is it accepting work? One that only proves the process is alive will keep routing traffic to a server that is broken.',
      ],
    },
    {
      title: 'A server dies, and users don’t notice',
      nodes: lbNodes({ s1: { badge: '200 OK', badgeTone: 'good' }, s2: { state: 'down', badge: 'TIMEOUT' }, s3: { badge: '200 OK', badgeTone: 'good' } }),
      flows: [
        F(['users', 'lb', 's1'], { dur: 2.1, n: 2 }),
        F(['users', 'lb', 's3'], { dur: 2.1, n: 2, offset: 0.25 }),
        F(['lb', 's2'], { type: 'ping', dur: 1.4 }),
      ],
      stats: [['Healthy', '2 / 3'], ['User-facing errors', '~0', 'good']],
      body: [
        'Server 2 stops answering. After a few failed checks the balancer removes it and spreads its share across servers 1 and 3. A handful of in-flight requests may fail, and clients that retry will succeed on the next attempt.',
        'This is why you plan for N+1 capacity. With one server gone, the rest must still carry peak load. Three servers that each run at 80% cannot absorb a lost peer.',
      ],
      takeaway: 'Redundancy only helps if the survivors have enough headroom.',
    },
    {
      title: 'Keep servers stateless',
      nodes: [...lbNodes(), N('sess', 'cache', 7, 0, 'Session store', { sub: 'shared, in-memory', state: 'focus' })],
      flows: [
        F(['users', 'lb', 's1', 'sess'], { dur: 2.8, offset: 0 }),
        F(['users', 'lb', 's2', 'sess'], { dur: 2.8, offset: 0.33 }),
        F(['users', 'lb', 's3', 'sess'], { dur: 2.8, offset: 0.66 }),
      ],
      body: [
        'If server 1 kept your login session in its own memory, your next request could land on server 3, which has never heard of you. One fix is sticky sessions: the balancer pins each user to one server. That works, but it spreads load unevenly, and everyone pinned to a server is logged out when it dies.',
        'The better fix keeps session state out of the servers entirely, either in a shared store such as Redis or in a signed token the client sends back with each request. Then any server can handle any request.',
      ],
    },
    {
      title: 'Who balances the balancer?',
      nodes: [
        N('users', 'client', 0, 0, 'Users', { scale: 1.15 }),
        N('lb', 'lb', 2.2, -0.7, 'LB (active)', { badge: 'VIP 203.0.113.10', badgeTone: 'good' }),
        N('lb2', 'lb', 2.2, 0.9, 'LB (standby)', { state: 'dim' }),
        N('s1', 'server', 5.2, -1.5, 'Server 1'),
        N('s2', 'server', 5.2, 0, 'Server 2'),
        N('s3', 'server', 5.2, 1.5, 'Server 3'),
      ],
      links: [['lb2', 's1'], ['lb2', 's2'], ['lb2', 's3']],
      flows: [
        F(['users', 'lb', 's1'], { dur: 2.1 }),
        F(['users', 'lb', 's2'], { dur: 2.1, offset: 1 / 3 }),
        F(['users', 'lb', 's3'], { dur: 2.1, offset: 2 / 3 }),
        F(['lb', 'lb2'], { type: 'ping', dur: 1 }),
      ],
      body: [
        'The load balancer is now a single point of failure. The standard fix is a pair: an active balancer holding a shared virtual IP, and a standby that watches its heartbeat. If the heartbeat stops, the standby takes over the IP within seconds.',
        'Cloud load balancers (AWS ELB, Google Cloud LB and others) do this for you behind a DNS name, and at a larger scale DNS itself can spread users across regions.',
      ],
      takeaway: 'Every layer needs a plan for losing one of its pieces, including the layer that handles failures for everything else.',
    },
  ],
};

const cacheBase = (extra = {}) => [
  N('users', 'client', 0, 0, 'Users'),
  N('app', 'server', 2.4, 0, 'App server', extra.app),
  N('cache', 'cache', 4.8, -1.3, 'Cache', { sub: 'Redis · in memory', ...extra.cache }),
  N('db', 'db', 5.2, 1.2, 'Database', extra.db),
];

const caching = {
  id: 'caching',
  title: 'Caching',
  steps: [
    {
      title: 'Every request goes to the database',
      nodes: [N('users', 'client', 0, 0, 'Users'), N('app', 'server', 2.4, 0, 'App server'), N('db', 'db', 5.2, 1.2, 'Database', { state: 'hot', badge: '40 ms / query' })],
      flows: [F(['users', 'app', 'db'], { n: 4 }), F(['db', 'app', 'users'], { type: 'res', n: 4, offset: 0.12 })],
      stats: [['p95 latency', '180 ms', 'bad'], ['DB load', '4,000 qps', 'bad']],
      body: [
        'Most applications read far more than they write. A product page or a profile might be viewed thousands of times between edits, and every one of those views runs the same query and returns the same rows.',
        'The database ends up doing the same work over and over, on disk, and it is usually the hardest part of the system to scale.',
      ],
    },
    {
      title: 'Cache hit',
      nodes: cacheBase({ cache: { badge: 'HIT user:42', badgeTone: 'good', state: 'focus' } }),
      flows: [F(['users', 'app', 'cache', 'app', 'users'], { n: 3, dur: 3 })],
      stats: [['Cache lookup', '< 1 ms', 'good'], ['Hit rate', '95%', 'good']],
      body: [
        'A cache is a fast key-value store, usually held in memory, that sits beside the database. Before running a query, the app first asks the cache for the result.',
        'If the cache has it (a hit), the app answers in well under a millisecond and never touches the database. With a 95% hit rate, the database sees only one in twenty reads.',
      ],
    },
    {
      title: 'Cache miss: cache-aside',
      nodes: cacheBase({ cache: { badge: 'MISS user:77', badgeTone: 'warn' } }),
      flows: [
        F(['app', 'cache', 'app'], { dur: 4.5, offset: 0 }),
        F(['app', 'db', 'app'], { dur: 4.5, offset: 0.33, type: 'res' }),
        F(['app', 'cache'], { dur: 4.5, offset: 0.7, type: 'data' }),
      ],
      body: [
        'On a miss, the app reads from the database as usual, then writes the result into the cache so the next reader gets a hit. The packets show the order: ask the cache, read the database, store the result in the cache.',
        'This pattern is called cache-aside (or lazy loading). Only data someone has actually asked for ends up in the cache, and if the cache goes down the app gets slower but still works.',
      ],
    },
    {
      title: 'Stale data and invalidation',
      nodes: cacheBase({ cache: { badge: 'DEL user:42', badgeTone: 'bad' }, db: { badge: 'UPDATE user:42', badgeTone: 'info' } }),
      flows: [F(['app', 'db'], { type: 'req', dur: 1.6 }), F(['app', 'cache'], { type: 'err', dur: 1.6, offset: 0.5 })],
      stats: [['TTL', '5 min']],
      body: [
        'Copies go stale. If a user renames themselves and the cache still holds the old name, readers will see wrong data until the entry changes.',
        'There are two common defences, usually used together. On every write, delete (invalidate) the cached key so the next read reloads it. Also give every entry a time-to-live (TTL), so anything you missed fixes itself after a few minutes.',
      ],
      takeaway: 'Invalidation is the hard part of caching. Decide how stale each kind of data is allowed to be.',
    },
    {
      title: 'Write-through and write-back',
      nodes: cacheBase({ cache: { state: 'focus', sub: 'writes pass through here' } }),
      flows: [F(['users', 'app', 'cache', 'db'], { n: 2, dur: 3 })],
      body: [
        'Cache-aside isn’t the only option. With write-through, every write goes to the cache and the database together. Reads are always warm, but each write pays for two stores.',
        'With write-back (write-behind), writes land in the cache and are flushed to the database later. Writes are very fast, but anything not yet flushed is lost if the cache crashes. That trade-off is acceptable for view counters but not for payments.',
      ],
    },
    {
      title: 'Cache at the edge: CDNs',
      nodes: [
        N('users', 'client', 0, 0, 'Users', { sub: 'Tokyo' }),
        N('cdn', 'cdn', 2.2, 0, 'CDN edge', { sub: 'Tokyo PoP', state: 'focus', badge: 'HIT logo.png', badgeTone: 'good' }),
        N('origin', 'server', 5.5, 0, 'Origin', { sub: 'Virginia' }),
      ],
      flows: [F(['users', 'cdn', 'users'], { n: 4, dur: 1.6 }), F(['cdn', 'origin', 'cdn'], { type: 'res', dur: 5 })],
      stats: [['Edge RTT', '8 ms', 'good'], ['Origin RTT', '160 ms']],
      body: [
        'Distance costs time. A round trip from Tokyo to Virginia takes about 150 ms however fast your servers are. A content delivery network (CDN) keeps copies of your responses on servers close to users all over the world.',
        'Images, scripts, video and other cacheable responses are served from the nearby edge. Only misses and expired items go back to your origin. For many sites, a CDN is the cheapest big latency improvement available.',
      ],
    },
    {
      title: 'Pitfall: the thundering herd',
      nodes: cacheBase({ cache: { badge: 'EXPIRED home:feed', badgeTone: 'bad' }, db: { state: 'hot', badge: '900 identical queries' } }),
      flows: [F(['users', 'app', 'cache'], { n: 3, dur: 2 }), F(['app', 'db'], { type: 'err', n: 6, dur: 1.6 })],
      stats: [['DB load', '×20 spike', 'bad']],
      body: [
        'A very popular key expires, and in the same instant hundreds of requests miss. Each one queries the database for the same thing, and the database falls over. This is called a cache stampede, or thundering herd.',
        'There are a few fixes. Let only one request rebuild the key while the others wait or briefly get the stale value (request coalescing). Refresh hot keys before they expire. Add random jitter to TTLs so keys don’t all expire together.',
      ],
    },
  ],
};

const databases = {
  id: 'databases',
  title: 'Scaling the database',
  steps: [
    {
      title: 'One primary does everything',
      nodes: [N('app', 'server', 0, 0, 'App servers', { scale: 1.1 }), N('p', 'db', 3.5, 0, 'Primary', { state: 'hot', badge: 'reads + writes' })],
      flows: [F(['app', 'p'], { n: 5 }), F(['app', 'p'], { type: 'msg', n: 1, offset: 0.5 }), F(['p', 'app'], { type: 'res', n: 3, offset: 0.2 })],
      stats: [['Reads', '9,000 qps'], ['Writes', '400 qps'], ['CPU', '92%', 'bad']],
      body: [
        'Once the app tier scales out, all those servers send their queries to one database. In this example, reads outnumber writes by more than twenty to one, which is common.',
        'Caching takes care of the hottest reads. What remains needs more database capacity, and the right approach depends on whether reads or writes are the bottleneck.',
      ],
    },
    {
      title: 'Read replicas',
      nodes: [
        N('app', 'server', 0, 0, 'App servers', { scale: 1.1 }),
        N('p', 'db', 3.5, -1.4, 'Primary', { sub: 'writes', state: 'focus' }),
        N('r1', 'db', 4.2, 0.6, 'Replica 1', { sub: 'reads' }),
        N('r2', 'db', 2.4, 2, 'Replica 2', { sub: 'reads' }),
      ],
      flows: [
        F(['app', 'p'], { type: 'msg', dur: 1.8 }),
        F(['app', 'r1'], { n: 2, dur: 1.8, offset: 0.25 }),
        F(['app', 'r2'], { n: 2, dur: 1.8 }),
        F(['p', 'r1'], { type: 'data', dur: 1.6 }),
        F(['p', 'r2'], { type: 'data', dur: 1.6, offset: 0.4 }),
      ],
      stats: [['Read capacity', '×3', 'good'], ['Write capacity', '×1']],
      body: [
        'Replication streams every change from the primary to one or more replicas, which keep identical copies of the data. Writes (orange) still go to the primary, while reads (blue) are spread across the replicas.',
        'Adding replicas increases read capacity roughly in proportion. It does nothing for writes, because every replica still has to apply every write.',
      ],
    },
    {
      title: 'Replication lag',
      nodes: [
        N('app', 'server', 0, 0, 'App servers', { scale: 1.1 }),
        N('p', 'db', 3.5, -1.4, 'Primary', { badge: 'name = "Kent"', badgeTone: 'good' }),
        N('r1', 'db', 4.2, 0.6, 'Replica 1', { badge: 'lag 2 s · "Ken"', badgeTone: 'warn' }),
        N('r2', 'db', 2.4, 2, 'Replica 2'),
      ],
      flows: [F(['app', 'p'], { type: 'msg', dur: 3, offset: 0 }), F(['app', 'r1', 'app'], { dur: 3, offset: 0.4 }), F(['p', 'r1'], { type: 'data', dur: 3 })],
      body: [
        'Most replication is asynchronous: the primary confirms a write before the replicas have applied it. Usually the gap is milliseconds, but under load it can grow to seconds.',
        'The classic bug: a user saves their profile, the page reloads from a replica, and their old name shows up again. A common fix is read-your-writes, where for a short time after a user writes, their own reads go to the primary.',
      ],
      takeaway: 'Replicas are eventually consistent. Decide which reads need to be fresh.',
    },
    {
      title: 'Failover',
      nodes: [
        N('app', 'server', 0, 0, 'App servers', { scale: 1.1 }),
        N('p', 'db', 3.5, -1.4, 'Old primary', { state: 'down', badge: 'DISK FAILED' }),
        N('r1', 'db', 4.2, 0.6, 'New primary', { state: 'focus', badge: 'PROMOTED', badgeTone: 'good' }),
        N('r2', 'db', 2.4, 2, 'Replica 2'),
      ],
      flows: [F(['app', 'r1'], { type: 'msg', dur: 1.8 }), F(['app', 'r2'], { n: 2, dur: 1.8 }), F(['r1', 'r2'], { type: 'data', dur: 1.8 })],
      stats: [['Failover time', '~30 s'], ['Data lost', '≤ lag window', 'bad']],
      body: [
        'When the primary dies, a replica is promoted to take its place, and the remaining replicas and the app servers are pointed at it. Managed databases such as RDS and Cloud SQL automate this.',
        'With asynchronous replication, any writes the old primary confirmed but never shipped are lost. Systems that cannot lose a single write use synchronous replication to at least one replica, and accept slower writes in return.',
      ],
    },
    {
      title: 'Sharding: split the data',
      nodes: [
        N('app', 'server', 0, 0, 'App servers', { scale: 1.1, sub: 'shard = hash(user_id) % 3' }),
        N('d1', 'db', 3.8, -1.6, 'Shard 0', { sub: 'users 0, 3, 6…' }),
        N('d2', 'db', 4.2, 0, 'Shard 1', { sub: 'users 1, 4, 7…' }),
        N('d3', 'db', 3.8, 1.6, 'Shard 2', { sub: 'users 2, 5, 8…' }),
      ],
      flows: [
        F(['app', 'd1'], { type: 'msg', dur: 1.8 }),
        F(['app', 'd2'], { dur: 1.8, offset: 0.33 }),
        F(['app', 'd3'], { type: 'msg', dur: 1.8, offset: 0.66 }),
        F(['app', 'd2'], { type: 'msg', dur: 1.8, offset: 0.1 }),
        F(['app', 'd3'], { dur: 1.8, offset: 0.4 }),
      ],
      stats: [['Write capacity', '×3', 'good'], ['Data per node', '⅓', 'good']],
      body: [
        'When writes or total data outgrow one machine, you split the data itself. Each shard is an independent database holding a slice of the rows, and a shard key such as user_id decides which shard a row lives on.',
        'Every shard handles only its own share of reads and writes, so capacity grows with the number of shards. Each shard usually has replicas of its own.',
      ],
    },
    {
      title: 'The cost of sharding',
      nodes: [
        N('app', 'server', 0, 0, 'App servers', { scale: 1.1 }),
        N('d1', 'db', 3.8, -1.6, 'Shard 0', { state: 'hot', badge: 'celebrity user', badgeTone: 'bad' }),
        N('d2', 'db', 4.2, 0, 'Shard 1', { state: 'dim' }),
        N('d3', 'db', 3.8, 1.6, 'Shard 2', { state: 'dim' }),
      ],
      flows: [F(['app', 'd1'], { n: 6, dur: 1.8 }), F(['app', 'd2'], { dur: 1.8 }), F(['app', 'd3'], { dur: 1.8, offset: 0.5 })],
      body: [
        'Sharding buys capacity at the price of complexity. A bad shard key creates hot spots: one shard holds the celebrity everyone follows and melts while the others sit idle. Queries that span shards, such as joins, global counts or unique constraints, become slow or impossible.',
        'Adding shards later means moving data. Plain hash % N reshuffles almost every key when N changes, so systems use consistent hashing or a directory of key ranges, which only move a small fraction.',
      ],
      takeaway: 'Shard last. Exhaust indexes, caching, replicas and bigger hardware first.',
    },
  ],
};

const queues = {
  id: 'queues',
  title: 'Message queues',
  steps: [
    {
      title: 'Doing everything inside the request',
      nodes: [
        N('users', 'client', 0, 0, 'Users'),
        N('app', 'server', 2.6, 0, 'App server', { badge: 'POST /signup', badgeTone: 'info' }),
        N('mail', 'service', 5.4, 0, 'Email provider', { state: 'hot', badge: '1.8 s', badgeTone: 'bad' }),
      ],
      flows: [F(['users', 'app', 'mail'], { dur: 3.2 }), F(['mail', 'app', 'users'], { type: 'res', dur: 3.2, offset: 0.5 })],
      stats: [['Sign-up latency', '2.1 s', 'bad'], ['If email is down', 'sign-up fails', 'bad']],
      body: [
        'A user signs up. Before responding, the app creates the account and also sends a welcome email, resizes the avatar and notifies analytics, while the user waits for all of it.',
        'The request is now as slow as its slowest dependency, and it fails whenever any one of them fails. An outage at the email provider stops people from signing up.',
      ],
    },
    {
      title: 'Put a queue in between',
      nodes: [
        N('users', 'client', 0, 0, 'Users'),
        N('app', 'server', 2.4, 0, 'App server', { badge: '201 Created · 60 ms', badgeTone: 'good' }),
        N('q', 'queue', 4.6, 0, 'Queue', { depth: 2, state: 'focus' }),
        N('w', 'worker', 6.6, 0, 'Worker'),
        N('mail', 'service', 8.4, 0, 'Email provider'),
      ],
      flows: [
        F(['users', 'app', 'users'], { dur: 1.8, n: 2 }),
        F(['app', 'q'], { type: 'msg', dur: 1.2 }),
        F(['q', 'w', 'mail'], { type: 'msg', dur: 2.6, offset: 0.3 }),
      ],
      stats: [['Sign-up latency', '60 ms', 'good']],
      body: [
        'Instead of sending the email itself, the app drops a small message, “send welcome email to user 42”, onto a queue and responds immediately. A separate worker process takes messages off the queue and does the slow work.',
        'Producer and consumer are now decoupled. Each can be deployed, scaled and fail independently. If the email provider is down, messages wait safely in the queue until it recovers.',
      ],
    },
    {
      title: 'Absorbing a spike',
      nodes: [
        N('users', 'client', 0, 0, 'Users', { sub: 'launch day!', scale: 1.2 }),
        N('app', 'server', 2.4, 0, 'App server'),
        N('q', 'queue', 4.6, 0, 'Queue', { depth: 8, badge: 'backlog 12,400', badgeTone: 'warn' }),
        N('w', 'worker', 6.6, 0, 'Worker', { sub: 'steady 50 / s' }),
        N('mail', 'service', 8.4, 0, 'Email provider'),
      ],
      flows: [F(['users', 'app', 'q'], { type: 'msg', n: 7, dur: 2 }), F(['q', 'w', 'mail'], { type: 'msg', dur: 2.6 })],
      stats: [['Incoming', '400 / s'], ['Processing', '50 / s'], ['App errors', '0', 'good']],
      body: [
        'Traffic jumps eight times over. Without a queue, everything downstream would get eight times the load all at once. With one, the backlog grows while the workers keep going at a steady pace they can sustain.',
        'This is load leveling: the queue acts as a shock absorber. The cost is delay, since some emails arrive minutes late, and for background work that is usually fine. Watch queue depth and the age of the oldest message. Those two numbers tell you when you need more workers.',
      ],
    },
    {
      title: 'Scale the consumers',
      nodes: [
        N('users', 'client', 0, 0, 'Users', { scale: 1.2 }),
        N('app', 'server', 2.4, 0, 'App server'),
        N('q', 'queue', 4.6, 0, 'Queue', { depth: 3, badge: 'backlog 900', badgeTone: 'good' }),
        N('w1', 'worker', 6.8, -1.4, 'Worker 1'),
        N('w2', 'worker', 6.8, 0, 'Worker 2'),
        N('w3', 'worker', 6.8, 1.4, 'Worker 3'),
      ],
      flows: [
        F(['users', 'app', 'q'], { type: 'msg', n: 5, dur: 2 }),
        F(['q', 'w1'], { type: 'msg', dur: 1.2, n: 2 }),
        F(['q', 'w2'], { type: 'msg', dur: 1.2, n: 2, offset: 0.17 }),
        F(['q', 'w3'], { type: 'msg', dur: 1.2, n: 2, offset: 0.34 }),
      ],
      stats: [['Processing', '150 / s', 'good']],
      body: [
        'Workers are stateless, so you scale them like app servers: run more copies. They pull from the same queue, and each message is handed to exactly one of them. Many setups autoscale the worker count on queue depth.',
        'With more than one worker, messages may finish out of order. If order matters, for example the events of a single account, partition the queue by key. Kafka and SQS FIFO both support this.',
      ],
    },
    {
      title: 'Failures, retries and dead letters',
      nodes: [
        N('app', 'server', 2.4, 0, 'App server'),
        N('q', 'queue', 4.6, 0, 'Queue', { depth: 3 }),
        N('w', 'worker', 6.8, 0, 'Worker', { badge: 'crashed mid-job', badgeTone: 'bad' }),
        N('dlq', 'queue', 4.8, 2.2, 'Dead-letter queue', { depth: 1, badge: 'failed 5×', badgeTone: 'bad' }),
      ],
      flows: [F(['q', 'w'], { type: 'msg', dur: 2.4 }), F(['w', 'q'], { type: 'err', dur: 2.4, offset: 0.5 }), F(['q', 'dlq'], { type: 'err', dur: 3 })],
      body: [
        'A worker only acknowledges a message after it finishes the job. If it crashes first, the message becomes visible again and another worker retries it. This gives at-least-once delivery, which means a job may run twice, so jobs must be idempotent. Sending the same welcome email twice should be detected and skipped.',
        'Some messages will never succeed, for example because of malformed data or a deleted user. After N attempts, often with exponential backoff, they move to a dead-letter queue, where a person can look at them without blocking everything else.',
      ],
      takeaway: 'Assume every message can arrive twice, late or out of order, and design jobs to handle it.',
    },
    {
      title: 'Publish once, fan out to many',
      nodes: [
        N('app', 'server', 0.6, 0, 'App server', { badge: 'user.signed_up', badgeTone: 'info' }),
        N('topic', 'queue', 3, 0, 'Topic', { depth: 1, state: 'focus' }),
        N('email', 'worker', 5.4, -1.6, 'Email'),
        N('analytics', 'worker', 5.8, 0, 'Analytics'),
        N('search', 'worker', 5.4, 1.6, 'Search index'),
      ],
      flows: [
        F(['app', 'topic'], { type: 'msg', dur: 1.2 }),
        F(['topic', 'email'], { type: 'msg', dur: 1.4, offset: 0.4 }),
        F(['topic', 'analytics'], { type: 'msg', dur: 1.4, offset: 0.4 }),
        F(['topic', 'search'], { type: 'msg', dur: 1.4, offset: 0.4 }),
      ],
      body: [
        'A queue hands each message to one consumer. A topic (publish/subscribe) gives every subscriber its own copy. The app announces that something happened, “user signed up”, without knowing or caring who is listening.',
        'Adding a new feature such as a CRM sync becomes a new subscriber rather than a change to the sign-up code. This event-driven style keeps services loosely coupled, at the cost of a flow that is harder to trace end to end.',
      ],
      takeaway: 'Queues spread work across consumers. Topics broadcast facts to every subscriber.',
    },
  ],
};

export const lessons = [scaling, loadBalancing, caching, databases, queues];

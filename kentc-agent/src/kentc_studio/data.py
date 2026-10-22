"""Data pulls: fixed, parameterised SQL queries against bank databases, run as studio jobs without the model.

A pull binds the case's app fields (e.g. :cif, :lookback_date, :start_date) and :case_id into its SQL, streams the
rows to cases/<id>/data/<pull>.csv and profiles them with its key-value queries: plain SQL over a `result` table
that holds the rows. No model is involved, so pulls run in parallel with the agents and do not hold the local
model; the report job waits for them like it waits for the insight agents. An app lists the pulls it offers; each
pull may only bind that app's fields (checked when the app loads).

config/studio.yaml (paths relative to it):

    databases:
      core: {url: "sqlite:///../../dataset/core-banking/core_banking.sqlite", label: Core banking, timeout: 1800,
             row_cap: 200000}
    data_pulls:
      txn_history:
        database: core
        label: Transaction history
        sql_file: ../queries/txn_history.sql
        default: true                    # pre-ticked on Page 1 (or `triggers: [adverse media, ...]`)
        key_values:
          Transactions: SELECT COUNT(*) FROM result
"""

from __future__ import annotations

import csv
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kentc_agent.agent import Aborted, Events

BIND_RE = re.compile(r"(?<![:\w]):([A-Za-z_]\w*)")
FETCH_ROWS = 2000
PREVIEW_ROWS = 15
TABLE_ROWS = 20


class DataError(RuntimeError):
    pass


def fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}"
    return str(v)


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@dataclass
class Database:
    name: str
    label: str
    path: Path
    timeout: float = 1800          # seconds before the query is interrupted
    row_cap: int = 200_000         # rows kept; the result is marked truncated beyond this
    latency: float = 0             # mock databases only: hold each pull this long to imitate a slow warehouse

    def connect(self) -> sqlite3.Connection:
        if not self.path.is_file():
            raise DataError(f"database {self.name}: {self.path} not found")
        return sqlite3.connect(f"{self.path.as_uri()}?mode=ro", uri=True)      # read-only


@dataclass
class DataPull:
    name: str
    label: str
    database: Database
    sql: str
    description: str = ""
    default: bool = False
    triggers: list[str] = field(default_factory=list)
    key_values: dict[str, str] = field(default_factory=dict)

    local = False                  # never holds the local model: runs in parallel with the agents

    @property
    def binds(self) -> list[str]:
        """The parameters this pull uses (case fields and :case_id), in order of first use."""
        return list(dict.fromkeys(BIND_RE.findall(self.sql + "\n" + "\n".join(self.key_values.values()))))

    def describe(self) -> str:
        return f"SQL on {self.database.label}"

    def selected_for(self, text: str) -> bool:
        """Pre-ticked for a case whose fields contain this text."""
        t = text.lower()
        return self.default or any(k.lower() in t for k in self.triggers)

    # -------------------------------------------------------------- running
    def run(self, *, case_dir: Path, job_dir: Path, inputs: dict[str, Any], events: Events, **_: Any) -> dict[str, Any]:
        db = self.database
        cancelled = getattr(events, "cancelled", lambda: False)
        t0 = time.monotonic()
        state = {"why": "", "shown": t0, "rows": 0}

        def progress(now: float) -> None:
            every = 3 if now - t0 < 60 else 15
            if now - state["shown"] >= every:
                state["shown"] = now
                rows = f" · {state['rows']:,} rows" if state["rows"] else ""
                events.status(self.name, f"querying {db.label} · {now - t0:.0f}s{rows}")

        def guard() -> int:        # sqlite progress handler: non-zero interrupts the statement
            now = time.monotonic()
            if cancelled():
                state["why"] = "stopped"
            elif now - t0 > db.timeout:
                state["why"] = "timeout"
            else:
                try:
                    progress(now)
                except Aborted:
                    state["why"] = "stopped"
            return 1 if state["why"] else 0

        out = case_dir / "data" / f"{self.name}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        events.status(self.name, f"querying {db.label}")
        con, mem = db.connect(), sqlite3.connect(":memory:")
        truncated, rows = False, 0
        try:
            con.set_progress_handler(guard, 20_000)
            try:
                cur = con.execute(self.sql, inputs)
                if cur.description is None:
                    raise DataError(f"{self.label}: the SQL must be a SELECT")
                columns = [c[0] for c in cur.description]
                mem.execute(f"CREATE TABLE result ({', '.join(quote(c) for c in columns)})")
                insert = f"INSERT INTO result VALUES ({', '.join('?' * len(columns))})"
                with out.open("w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(columns)
                    while batch := cur.fetchmany(FETCH_ROWS):
                        if rows + len(batch) > db.row_cap:
                            batch, truncated = batch[:db.row_cap - rows], True
                        w.writerows(batch)
                        mem.executemany(insert, batch)
                        rows += len(batch)
                        state["rows"] = rows
                        if truncated:
                            break
            except sqlite3.Error as e:
                if state["why"] == "stopped":
                    raise Aborted() from None
                if state["why"] == "timeout":
                    raise DataError(f"{self.label}: timed out after {db.timeout:.0f}s") from None
                raise DataError(f"{self.label}: {e}") from None
            seconds = time.monotonic() - t0
            self._hold(t0, events, cancelled)
            key_values = self._profile(mem, columns, rows, inputs)
            preview = [[fmt(v) for v in r] for r in mem.execute(f"SELECT * FROM result LIMIT {PREVIEW_ROWS}")]
        finally:
            con.close()
            mem.close()
        events.status(self.name, f"{rows:,} rows{' (capped)' if truncated else ''} in {seconds:.1f}s")
        return {"pull": self.name, "label": self.label, "database": db.label,
                "params": {k: inputs.get(k, "") for k in self.binds}, "sql": self.sql.strip(),
                "columns": columns, "rows": rows, "truncated": truncated, "row_cap": db.row_cap,
                "seconds": round(seconds, 2), "file": f"data/{self.name}.csv", "preview": preview,
                "key_values": key_values}

    def _hold(self, t0: float, events: Events, cancelled) -> None:
        """Mock databases answer at once; `latency` makes the pull take that long so the asynchronous flow shows."""
        db = self.database
        while (left := db.latency - (time.monotonic() - t0)) > 0:
            if cancelled():
                raise Aborted()
            events.status(self.name, f"querying {db.label} · {time.monotonic() - t0:.0f}s "
                                     f"(mock latency {db.latency:.0f}s)")
            time.sleep(min(3.0, left))

    def _profile(self, mem: sqlite3.Connection, columns: list[str], rows: int,
                 params: dict[str, Any]) -> list[dict[str, Any]]:
        """Key values: each `key_values` query over `result` gives a value (1x1) or a small table; without
        queries, a one-row result gives one key value per column."""
        if not self.key_values:
            if rows == 1:
                row = mem.execute("SELECT * FROM result").fetchone()
                return [{"field": c, "value": fmt(v)} for c, v in zip(columns, row)]
            return [{"field": "Rows", "value": f"{rows:,}"}]
        out: list[dict[str, Any]] = []
        for label, sql in self.key_values.items():
            try:
                cur = mem.execute(sql, params)
                cols = [c[0] for c in cur.description or []]
                data = cur.fetchmany(TABLE_ROWS)
            except sqlite3.Error as e:
                out.append({"field": label, "value": f"[key-value query error: {e}]"})
                continue
            if len(cols) == 1 and len(data) <= 1:
                out.append({"field": label, "value": fmt(data[0][0]) if data else ""})
            else:
                out.append({"field": label, "columns": cols, "rows": [[fmt(v) for v in r] for r in data]})
        return out


# ---------------------------------------------------------------------- config
def _database(name: str, spec: dict[str, Any], base: Path) -> Database:
    url = str(spec.get("url") or "")
    if not url.startswith("sqlite:///"):
        raise DataError(f"database {name}: url must be sqlite:///<path> (studio/data.py connects to SQLite; add a "
                        "driver there for another engine)")
    path = Path(url.removeprefix("sqlite:///"))
    return Database(name, str(spec.get("label") or name), path if path.is_absolute() else (base / path).resolve(),
                    float(spec.get("timeout", 1800)), int(spec.get("row_cap", 200_000)),
                    float(spec.get("latency", 0)))


def load_pulls(raw: dict[str, Any], base: Path) -> dict[str, DataPull]:
    dbs = {k: _database(k, v or {}, base) for k, v in (raw.get("databases") or {}).items()}
    pulls = {}
    for name, spec in (raw.get("data_pulls") or {}).items():
        spec = spec or {}
        db = dbs.get(spec.get("database", ""))
        if db is None:
            raise DataError(f"data pull {name}: database must be one of {', '.join(dbs) or '(none configured)'}")
        sql_file = base / str(spec.get("sql_file") or "")
        if not spec.get("sql_file") or not sql_file.is_file():
            raise DataError(f"data pull {name}: sql_file {sql_file} not found")
        pulls[name] = DataPull(name, str(spec.get("label") or name), db, sql_file.read_text(encoding="utf-8"),
                               str(spec.get("description") or ""), bool(spec.get("default")),
                               [str(t) for t in spec.get("triggers") or []],
                               {str(k): str(v) for k, v in (spec.get("key_values") or {}).items()})
    return pulls

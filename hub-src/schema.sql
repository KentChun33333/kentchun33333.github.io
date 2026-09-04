PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS assets (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL, stream TEXT NOT NULL,
 path TEXT NOT NULL UNIQUE, summary TEXT NOT NULL, status TEXT NOT NULL,
 visibility TEXT NOT NULL CHECK(visibility = 'public'), metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
 asset_id TEXT NOT NULL REFERENCES assets(id), sha256 TEXT NOT NULL, observed_at TEXT NOT NULL,
 PRIMARY KEY(asset_id, sha256)
);
CREATE TABLE IF NOT EXISTS relations (
 source TEXT NOT NULL REFERENCES assets(id), type TEXT NOT NULL,
 target TEXT NOT NULL REFERENCES assets(id), basis TEXT NOT NULL,
 PRIMARY KEY(source, type, target), CHECK(source != target)
);
CREATE TABLE IF NOT EXISTS offers (
 id TEXT PRIMARY KEY, title TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('inquiry', 'available', 'retired')),
 metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS offer_assets (
 offer_id TEXT NOT NULL REFERENCES offers(id), asset_id TEXT NOT NULL REFERENCES assets(id),
 PRIMARY KEY(offer_id, asset_id)
);
CREATE TABLE IF NOT EXISTS source_inventory (
 path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_kind_stream ON assets(kind, stream);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target);

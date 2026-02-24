-- GM-AI-Hub 초기 스키마

-- 문서 인덱스
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT UNIQUE NOT NULL,
    filename    TEXT NOT NULL,
    ext         TEXT NOT NULL,
    size_bytes  INTEGER,
    text_hash   TEXT,
    indexed_at  TEXT DEFAULT (datetime('now')),
    metadata    TEXT
);

-- 전문 검색 (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    path UNINDEXED,
    filename,
    content,
    tokenize = 'unicode61'
);

-- 임베딩 벡터
CREATE TABLE IF NOT EXISTS embeddings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    vector_json TEXT NOT NULL
);

-- 감사 로그 (문서 내용은 절대 기록하지 않음)
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT DEFAULT (datetime('now')),
    action      TEXT NOT NULL,
    file_path   TEXT,
    model       TEXT,
    duration_ms INTEGER,
    success     INTEGER,
    error       TEXT
);

-- 설정
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- 법령 DB
CREATE TABLE IF NOT EXISTS regulations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    law_name    TEXT NOT NULL,
    article     TEXT NOT NULL,
    content     TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS regulations_fts USING fts5(
    law_name, article, content,
    tokenize = 'unicode61'
);

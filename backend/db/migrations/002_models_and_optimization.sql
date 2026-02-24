-- v1.1 다중 모델 + MIPROv2 최적화

-- 모델 사용 이력
CREATE TABLE IF NOT EXISTS model_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    used_at     TEXT DEFAULT (datetime('now')),
    model       TEXT NOT NULL,
    task        TEXT NOT NULL,
    duration_ms INTEGER,
    tokens      INTEGER,
    success     INTEGER,
    reasoning   TEXT
);

-- 최적화 이력
CREATE TABLE IF NOT EXISTS optimization_history (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline                  TEXT NOT NULL,
    model                     TEXT NOT NULL,
    last_optimized_at         TEXT DEFAULT (datetime('now')),
    val_score                 REAL,
    num_trials                INTEGER,
    train_examples            INTEGER,
    doc_count_at_optimization INTEGER,
    save_path                 TEXT
);

-- 모델 평가 기록
CREATE TABLE IF NOT EXISTS model_evaluations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluated_at TEXT DEFAULT (datetime('now')),
    model       TEXT NOT NULL,
    pipeline    TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    score       REAL NOT NULL
);

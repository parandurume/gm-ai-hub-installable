-- 008: 채팅 이미지 저장 테이블
CREATE TABLE IF NOT EXISTS chat_images (
    id TEXT PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'image/jpeg',
    file_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_chat_images_session ON chat_images(session_id);

-- chat_messages에 images 컬럼 추가 (JSON 배열 of image IDs)
ALTER TABLE chat_messages ADD COLUMN images TEXT;

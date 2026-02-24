-- 앱 초기 설정 (셋업 위저드 완료 상태 추적)
-- settings 테이블은 001_initial.sql에서 이미 생성됨

-- 기본 설정값 삽입 (setup_completed = false)
INSERT OR IGNORE INTO settings (key, value) VALUES ('setup_completed', 'false');
INSERT OR IGNORE INTO settings (key, value) VALUES ('department_name', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('officer_name', '');

#!/usr/bin/env bash
# USB 배포용 패키지 준비 스크립트 (RULE-10: 멱등성 보장)
# 사용법: bash scripts/prepare_usb.sh [출력_디렉토리]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${1:-$PROJECT_DIR/dist/usb-package}"

echo "=== GM-AI-Hub USB 패키지 준비 ==="
echo "프로젝트: $PROJECT_DIR"
echo "출력: $OUTPUT_DIR"

# 1. 출력 디렉토리 (멱등: 이미 존재해도 OK)
mkdir -p "$OUTPUT_DIR"

# 2. 프론트엔드 빌드
echo ""
echo "[1/5] 프론트엔드 빌드..."
if [ -d "$PROJECT_DIR/frontend" ]; then
    cd "$PROJECT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        npm install --production 2>/dev/null || echo "WARN: npm install 실패 (node가 없을 수 있음)"
    fi
    npx vite build 2>/dev/null || echo "WARN: vite build 실패"
    cd "$PROJECT_DIR"
fi

# 3. 필수 파일 복사
echo "[2/5] 파일 복사..."
# 백엔드
mkdir -p "$OUTPUT_DIR/backend"
cp -r "$PROJECT_DIR/backend/"* "$OUTPUT_DIR/backend/" 2>/dev/null || true

# MCP 서버
mkdir -p "$OUTPUT_DIR/mcp_server"
cp -r "$PROJECT_DIR/mcp_server/"* "$OUTPUT_DIR/mcp_server/" 2>/dev/null || true

# 데이터 (템플릿, 예제)
mkdir -p "$OUTPUT_DIR/data"
cp -r "$PROJECT_DIR/data/"* "$OUTPUT_DIR/data/" 2>/dev/null || true

# 프론트엔드 빌드 결과
if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    mkdir -p "$OUTPUT_DIR/frontend/dist"
    cp -r "$PROJECT_DIR/frontend/dist/"* "$OUTPUT_DIR/frontend/dist/" 2>/dev/null || true
fi

# 스크립트
mkdir -p "$OUTPUT_DIR/scripts"
cp "$PROJECT_DIR/scripts/install_govpc.bat" "$OUTPUT_DIR/scripts/" 2>/dev/null || true
cp "$PROJECT_DIR/scripts/verify_setup.py" "$OUTPUT_DIR/scripts/" 2>/dev/null || true

# 설정 파일
cp "$PROJECT_DIR/pyproject.toml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/.env.example" "$OUTPUT_DIR/.env.example" 2>/dev/null || true

# 4. Python 의존성 다운로드 (오프라인 설치용)
echo "[3/5] Python 패키지 다운로드..."
mkdir -p "$OUTPUT_DIR/packages"
pip download -r <(python -c "
import tomllib
with open('$PROJECT_DIR/pyproject.toml', 'rb') as f:
    d = tomllib.load(f)
for dep in d.get('project', {}).get('dependencies', []):
    print(dep)
") -d "$OUTPUT_DIR/packages" 2>/dev/null || echo "WARN: pip download 일부 실패 (온라인 환경에서 실행하세요)"

# 5. Ollama 모델 목록 생성
echo "[4/5] 모델 정보 생성..."
cat > "$OUTPUT_DIR/MODELS.txt" << 'MODELS_EOF'
# GM-AI-Hub 필수 Ollama 모델 목록
# 아래 모델을 미리 다운로드하여 USB에 포함시키세요.
#
# 기본 모델 (필수):
ollama pull gpt-oss:20b
#
# 추가 모델 (선택):
ollama pull qwen3:8b
ollama pull qwen3:14b
ollama pull exaone3.5:7.8b
ollama pull deepseek-r1:8b
#
# 고사양 PC용:
ollama pull qwen3:32b
ollama pull qwen3.5:72b
MODELS_EOF

# 6. 완료
echo "[5/5] 패키지 크기 확인..."
du -sh "$OUTPUT_DIR" 2>/dev/null || dir "$OUTPUT_DIR"

echo ""
echo "=== USB 패키지 준비 완료 ==="
echo "출력 위치: $OUTPUT_DIR"
echo ""
echo "관공서 PC에 설치하려면:"
echo "  1. USB를 관공서 PC에 연결"
echo "  2. scripts/install_govpc.bat 실행"
echo "  3. .env 파일 설정 후 서버 시작"

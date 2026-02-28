/** API 엔드포인트 상수 + fetch 래퍼 */

const BASE = '/api'

export const API = {
  health:             `${BASE}/health`,
  healthOllama:       `${BASE}/health/ollama`,
  documents:          `${BASE}/documents`,
  draftTemplates:     `${BASE}/draft/templates`,
  draftGenerate:      `${BASE}/draft/generate`,
  draftAiBody:        `${BASE}/draft/ai-body`,
  draftSave:          `${BASE}/draft/save`,
  search:             `${BASE}/search`,
  chat:               `${BASE}/chat`,
  chatStream:         `ws://${location.host}${BASE}/chat/stream`,
  chatSessions:       `${BASE}/chat/sessions`,
  piiExportReport:    `${BASE}/pii/export-report`,
  meeting:            `${BASE}/meeting/create`,
  meetingStream:      `${BASE}/meeting/stream`,
  meetingTranscribe:  `${BASE}/meeting/transcribe`,
  meetingSttStatus:   `${BASE}/meeting/stt-status`,
  complaintClassify:  `${BASE}/complaint/classify`,
  complaintDraft:     `${BASE}/complaint/draft`,
  regulationSearch:   `${BASE}/regulation/search`,
  regulationStatus:   `${BASE}/regulation/status`,
  regulationSetOc:    `${BASE}/regulation/oc`,
  piiScanText:        `${BASE}/pii/scan-text`,
  piiScan:            `${BASE}/pii/scan`,
  piiMask:            `${BASE}/pii/mask`,
  piiBatchScan:       `${BASE}/pii/batch-scan`,
  draftValidate:      `${BASE}/draft/validate`,
  diff:               `${BASE}/diff`,
  settings:           `${BASE}/settings`,
  models:             `${BASE}/models`,
  modelsRecommend:    `${BASE}/models/recommend`,
  modelsPullStream:   `${BASE}/models/pull-stream`,
  optimizeStatus:     `${BASE}/optimize/status`,
  optimizeRun:        `${BASE}/optimize/run`,
  optimizeReload:     `${BASE}/optimize/reload`,
  filesystemBrowse:   `${BASE}/filesystem/browse`,
  samplesScan:        `${BASE}/samples/scan`,
  samplesExtract:     `${BASE}/samples/extract`,
  samplesPending:     `${BASE}/samples/pending`,
  samplesApprove:     `${BASE}/samples/approve`,
  samplesReject:      `${BASE}/samples/reject`,
  setupStatus:        `${BASE}/setup/status`,
  setupCheckOllama:   `${BASE}/setup/check-ollama`,
  setupComplete:      `${BASE}/setup/complete`,
  quit:               `${BASE}/quit`,
}

export async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    let detail = ''
    try { const body = await res.json(); detail = body.detail || body.message || '' } catch { /* not JSON */ }
    const err = new Error(detail || `HTTP ${res.status}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export function aiErrorMessage(taskName, err) {
  if (!err || err.message === 'Failed to fetch' || err.message?.includes('NetworkError')) {
    return `${taskName} 실패 — 서버에 연결할 수 없습니다. 앱이 실행 중인지 확인하세요.`
  }
  if (err.status === 503 || err.message?.includes('Ollama') || err.message?.includes('connection')) {
    return `${taskName} 실패 — AI 서버 응답 없음. Ollama가 실행 중인지 확인하세요.`
  }
  if (err.status === 504 || err.message?.includes('timeout')) {
    return `${taskName} 실패 — 응답 시간 초과. 더 작은 모델을 선택하거나 다시 시도하세요.`
  }
  if (err.message) {
    return `${taskName} 실패 — ${err.message}`
  }
  return `${taskName} 실패 — 알 수 없는 오류. 다시 시도하세요.`
}

export async function postJSON(url, body) {
  return fetchJSON(url, { method: 'POST', body: JSON.stringify(body) })
}

/** API 엔드포인트 상수 + fetch 래퍼 */

const BASE = '/api'

export const API = {
  health:             `${BASE}/health`,
  healthOllama:       `${BASE}/health/ollama`,
  documents:          `${BASE}/documents`,
  gianmunTemplates:   `${BASE}/gianmun/templates`,
  gianmunGenerate:    `${BASE}/gianmun/generate`,
  gianmunAiBody:      `${BASE}/gianmun/ai-body`,
  gianmunSave:        `${BASE}/gianmun/save`,
  search:             `${BASE}/search`,
  chat:               `${BASE}/chat`,
  chatStream:         `ws://${location.host}${BASE}/chat/stream`,
  meeting:            `${BASE}/meeting/create`,
  meetingTranscribe:  `${BASE}/meeting/transcribe`,
  meetingSttStatus:   `${BASE}/meeting/stt-status`,
  complaintClassify:  `${BASE}/complaint/classify`,
  complaintDraft:     `${BASE}/complaint/draft`,
  regulationSearch:   `${BASE}/regulation/search`,
  piiScan:            `${BASE}/pii/scan`,
  piiMask:            `${BASE}/pii/mask`,
  piiBatchScan:       `${BASE}/pii/batch-scan`,
  gianmunValidate:    `${BASE}/gianmun/validate`,
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
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postJSON(url, body) {
  return fetchJSON(url, { method: 'POST', body: JSON.stringify(body) })
}

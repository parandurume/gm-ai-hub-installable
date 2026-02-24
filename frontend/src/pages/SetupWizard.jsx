import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchJSON, postJSON, API } from '../utils/api'

const STEPS = ['welcome', 'ollama', 'models', 'info', 'ready']

export default function SetupWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [ollamaStatus, setOllamaStatus] = useState(null)
  const [checking, setChecking] = useState(false)
  const [form, setForm] = useState({
    department_name: '',
    officer_name: '',
    ollama_url: 'http://127.0.0.1:11434',
    ollama_model: 'gpt-oss:20b',
  })
  const [saving, setSaving] = useState(false)

  const currentStep = STEPS[step]
  const canNext = step < STEPS.length - 1
  const canPrev = step > 0

  async function checkOllama() {
    setChecking(true)
    try {
      const data = await fetchJSON(API.setupCheckOllama)
      setOllamaStatus(data)
    } catch {
      setOllamaStatus({ connected: false, installed_models: [], missing_models: [] })
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    if (currentStep === 'ollama' || currentStep === 'models') {
      checkOllama()
    }
  }, [step])

  async function handleComplete() {
    setSaving(true)
    try {
      await postJSON(API.setupComplete, form)
      navigate('/')
    } catch {
      alert('설정 저장에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setSaving(false)
    }
  }

  function updateForm(key, value) {
    setForm(f => ({ ...f, [key]: value }))
  }

  return (
    <div className="setup-wizard">
      <div className="setup-container">
        {/* Progress */}
        <div className="setup-progress">
          {STEPS.map((s, i) => (
            <div key={s} className={`setup-step-dot ${i <= step ? 'active' : ''} ${i === step ? 'current' : ''}`} />
          ))}
        </div>

        {/* Step: Welcome */}
        {currentStep === 'welcome' && (
          <div className="setup-step">
            <h1>GM-AI-Hub</h1>
            <p className="setup-subtitle">AI 공문서 작성 시스템</p>
            <div className="setup-description">
              <p>GM-AI-Hub는 지방자치단체 공무원을 위한 AI 기반 문서 작성 도구입니다.</p>
              <ul>
                <li>기안문 AI 작성 및 검토</li>
                <li>회의록 자동 요약</li>
                <li>민원 답변 초안 생성</li>
                <li>문서 검색 및 비교</li>
                <li>개인정보(PII) 자동 검사</li>
              </ul>
              <p>초기 설정을 진행하겠습니다. 약 2분이면 완료됩니다.</p>
            </div>
          </div>
        )}

        {/* Step: Ollama */}
        {currentStep === 'ollama' && (
          <div className="setup-step">
            <h2>AI 엔진 확인</h2>
            <p className="setup-subtitle">
              이 프로그램은 Ollama를 사용하여 AI 기능을 제공합니다.
              모든 데이터는 이 컴퓨터에서만 처리됩니다.
            </p>

            {checking ? (
              <div className="setup-check-status">확인 중...</div>
            ) : ollamaStatus ? (
              <div className="setup-check-result">
                <div className={`setup-status-badge ${ollamaStatus.connected ? 'success' : 'error'}`}>
                  {ollamaStatus.connected ? 'Ollama 연결됨' : 'Ollama 미연결'}
                </div>
                {!ollamaStatus.connected && (
                  <div className="setup-help">
                    <p>Ollama가 설치되어 있지 않거나 실행되지 않고 있습니다.</p>
                    <ol>
                      <li>
                        <a href="https://ollama.com/download" target="_blank" rel="noreferrer">
                          Ollama 다운로드 페이지
                        </a>에서 Windows용을 다운로드하세요.
                      </li>
                      <li>설치 후 Ollama가 자동으로 시작됩니다.</li>
                      <li>아래 버튼으로 다시 확인하세요.</li>
                    </ol>
                    <button className="btn btn-secondary" onClick={checkOllama}>다시 확인</button>
                  </div>
                )}
                {ollamaStatus.connected && (
                  <p className="setup-ok-text">Ollama가 정상적으로 실행 중입니다.</p>
                )}
              </div>
            ) : null}

            <div className="form-group" style={{ marginTop: 20 }}>
              <label>Ollama 주소</label>
              <input
                type="text"
                value={form.ollama_url}
                onChange={e => updateForm('ollama_url', e.target.value)}
                placeholder="http://127.0.0.1:11434"
              />
            </div>
          </div>
        )}

        {/* Step: Models */}
        {currentStep === 'models' && (
          <div className="setup-step">
            <h2>AI 모델 확인</h2>
            <p className="setup-subtitle">
              문서 작성에 필요한 AI 모델이 설치되어 있는지 확인합니다.
            </p>

            {checking ? (
              <div className="setup-check-status">모델 목록 확인 중...</div>
            ) : ollamaStatus?.connected ? (
              <>
                {ollamaStatus.installed_models.length > 0 && (
                  <div className="setup-model-list">
                    <h4>설치된 모델</h4>
                    {ollamaStatus.installed_models.map(m => (
                      <div key={m} className="setup-model-item installed">{m}</div>
                    ))}
                  </div>
                )}

                {ollamaStatus.missing_models?.length > 0 && (
                  <div className="setup-model-list" style={{ marginTop: 16 }}>
                    <h4>권장 모델 (미설치)</h4>
                    {ollamaStatus.missing_models.map(m => (
                      <div key={m.id} className="setup-model-item missing">
                        <div>
                          <strong>{m.name}</strong>
                          <span className="setup-model-desc">{m.description}</span>
                        </div>
                        <code className="setup-model-cmd">ollama pull {m.id}</code>
                      </div>
                    ))}
                    <p className="setup-help-text">
                      터미널(명령 프롬프트)에서 위 명령어를 실행하여 모델을 설치할 수 있습니다.
                      모델이 없어도 앱은 실행되지만, AI 기능이 제한됩니다.
                    </p>
                  </div>
                )}

                {ollamaStatus.missing_models?.length === 0 && (
                  <div className="setup-status-badge success" style={{ marginTop: 16 }}>
                    모든 권장 모델이 설치되어 있습니다
                  </div>
                )}

                <div className="form-group" style={{ marginTop: 20 }}>
                  <label>기본 모델</label>
                  <select
                    value={form.ollama_model}
                    onChange={e => updateForm('ollama_model', e.target.value)}
                  >
                    {ollamaStatus.installed_models.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                    <option value="gpt-oss:20b">gpt-oss:20b (기본)</option>
                  </select>
                </div>
              </>
            ) : (
              <div className="setup-status-badge error">
                Ollama에 연결할 수 없습니다. 이전 단계를 확인하세요.
              </div>
            )}

            <button className="btn btn-secondary" onClick={checkOllama} style={{ marginTop: 12 }}>
              다시 확인
            </button>
          </div>
        )}

        {/* Step: Info */}
        {currentStep === 'info' && (
          <div className="setup-step">
            <h2>기본 정보</h2>
            <p className="setup-subtitle">
              문서 작성 시 자동으로 입력되는 기본 정보를 설정합니다.
              나중에 설정 페이지에서 변경할 수 있습니다.
            </p>

            <div className="form-group">
              <label>부서명</label>
              <input
                type="text"
                value={form.department_name}
                onChange={e => updateForm('department_name', e.target.value)}
                placeholder="예: 정보통신과"
              />
            </div>
            <div className="form-group">
              <label>담당자 이름</label>
              <input
                type="text"
                value={form.officer_name}
                onChange={e => updateForm('officer_name', e.target.value)}
                placeholder="예: 홍길동"
              />
            </div>
          </div>
        )}

        {/* Step: Ready */}
        {currentStep === 'ready' && (
          <div className="setup-step">
            <h2>설정 완료</h2>
            <div className="setup-summary">
              <div className="setup-summary-row">
                <span>Ollama</span>
                <span className={`badge ${ollamaStatus?.connected ? 'badge-success' : 'badge-warning'}`}>
                  {ollamaStatus?.connected ? '연결됨' : '미연결'}
                </span>
              </div>
              {form.department_name && (
                <div className="setup-summary-row">
                  <span>부서</span>
                  <span>{form.department_name}</span>
                </div>
              )}
              {form.officer_name && (
                <div className="setup-summary-row">
                  <span>담당자</span>
                  <span>{form.officer_name}</span>
                </div>
              )}
              <div className="setup-summary-row">
                <span>모델</span>
                <span>{form.ollama_model}</span>
              </div>
            </div>
            <button
              className="btn btn-primary btn-large"
              onClick={handleComplete}
              disabled={saving}
            >
              {saving ? '저장 중...' : '시작하기'}
            </button>
          </div>
        )}

        {/* Navigation */}
        <div className="setup-nav">
          {canPrev && (
            <button className="btn btn-secondary" onClick={() => setStep(s => s - 1)}>
              이전
            </button>
          )}
          <div style={{ flex: 1 }} />
          {canNext && (
            <button className="btn btn-primary" onClick={() => setStep(s => s + 1)}>
              다음
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

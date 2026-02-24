import { useState, useEffect, memo } from 'react'
import { fetchJSON, API } from '../utils/api'

let cachedModels = null
let fetchPromise = null

function fetchModels() {
  if (cachedModels) return Promise.resolve(cachedModels)
  if (fetchPromise) return fetchPromise
  fetchPromise = fetchJSON(API.models)
    .then(data => {
      const models = data?.models?.filter(m => m.available) || []
      cachedModels = models
      return models
    })
    .catch(() => [])
    .finally(() => { fetchPromise = null })
  return fetchPromise
}

export default memo(function ModelSelector({ value, onChange }) {
  const [models, setModels] = useState(cachedModels || [])

  useEffect(() => {
    fetchModels().then(setModels)
  }, [])

  return (
    <div role="group" aria-label="AI 모델 선택">
      <div className="model-cards">
        <button
          type="button"
          className={`model-card ${!value ? 'active' : ''}`}
          onClick={() => onChange(null)}
        >
          <div className="model-name">자동 선택</div>
          <div className="model-meta">태스크에 맞는 모델</div>
        </button>
        {models.map(m => (
          <button
            type="button"
            key={m.id}
            className={`model-card ${value === m.id ? 'active' : ''}`}
            onClick={() => onChange(m.id)}
          >
            <div className="model-name">{m.name}</div>
            <div className="model-meta">
              {m.param_size}B · {m.ram_gb}GB
              {m.supports_thinking && ' · \uD83E\uDDE0'}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
})

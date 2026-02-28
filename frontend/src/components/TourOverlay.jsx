import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTour } from '../hooks/useTour'

export default function TourOverlay() {
  const { active, step, steps, nextStep, prevStep, endTour, totalSteps } = useTour()
  const navigate = useNavigate()

  const current = steps[step]
  const isFirst = step === 0
  const isLast = step === totalSteps - 1

  useEffect(() => {
    if (active && current?.path) {
      navigate(current.path)
    }
  }, [active, step, current?.path, navigate])

  if (!active) return null

  function handleNext() {
    if (isLast) {
      endTour(true)
    } else {
      nextStep()
    }
  }

  function handleSkip() {
    endTour(true)
  }

  return (
    <div className="tour-overlay">
      <div className="tour-card">
        <div className="tour-progress">
          {steps.map((_, i) => (
            <div key={i} className={`tour-progress-dot ${i === step ? 'active' : i < step ? 'done' : ''}`} />
          ))}
        </div>

        <div className="tour-icon">{current.icon}</div>
        <div className="tour-step-label">
          {step + 1} / {totalSteps}
        </div>
        <h3 className="tour-title">{current.title}</h3>
        <p className="tour-description">{current.description}</p>

        <div className="tour-actions">
          {!isFirst && (
            <button className="btn btn-secondary" onClick={prevStep}>이전</button>
          )}
          <div style={{ flex: 1 }} />
          {!isLast && (
            <button className="tour-skip-btn" onClick={handleSkip}>건너뛰기</button>
          )}
          <button className="btn btn-primary" onClick={handleNext}>
            {isLast ? '시작하기' : '다음'}
          </button>
        </div>
      </div>
    </div>
  )
}

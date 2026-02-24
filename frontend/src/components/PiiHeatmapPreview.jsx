/** PII 히트맵 미리보기 — 문서 위에 유형별 하이라이트, 클릭 네비게이션 */

import { useRef, useEffect, memo } from 'react'
import { buildSegments, maskPartial } from '../utils/textSegments'

const TYPE_HL_CLASS = {
  '주민등록번호': 'pii-hl-ssn',
  '전화번호':     'pii-hl-phone',
  '이메일':       'pii-hl-email',
  '주소':         'pii-hl-address',
  '계좌번호':     'pii-hl-bank',
  '여권번호':     'pii-hl-passport',
  '운전면허번호': 'pii-hl-license',
}

function PiiHeatmapPreview({ text, maskedText, findings = [], showMasked, activeIndex, onFindingHover }) {
  const containerRef = useRef(null)
  const spanRefs = useRef({})

  // activeIndex가 변경되면 해당 위치로 스크롤
  useEffect(() => {
    if (activeIndex == null) return
    const el = spanRefs.current[activeIndex]
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [activeIndex])

  const displayText = showMasked && maskedText ? maskedText : text
  if (!displayText) {
    return (
      <div className="preview-empty">
        <span style={{ fontSize: 48 }}>{'📄'}</span>
        <span>문서를 스캔하면 히트맵이 표시됩니다</span>
      </div>
    )
  }

  // findings를 markers 형태로 변환
  const markers = findings.map((f, i) => ({
    ...f,
    _index: i,
  }))

  const segments = buildSegments(displayText, markers)
  let findingIdx = -1

  return (
    <div className="preview-body pii-heatmap" ref={containerRef} style={{ whiteSpace: 'pre-wrap' }}>
      {segments.map((seg, i) => {
        if (!seg.marker) {
          return <span key={i}>{seg.text}</span>
        }

        findingIdx++
        const idx = seg.marker._index != null ? seg.marker._index : findingIdx
        const typeClass = TYPE_HL_CLASS[seg.marker.type] || 'pii-highlight'
        const isActive = activeIndex === idx

        const displayVal = showMasked ? seg.text : maskPartial(seg.text)

        return (
          <span
            key={i}
            ref={el => { spanRefs.current[idx] = el }}
            className={`pii-highlight ${typeClass}${isActive ? ' pii-hl-active' : ''}`}
            title={seg.marker.type}
            onMouseEnter={() => onFindingHover?.(idx)}
            onClick={() => onFindingHover?.(idx)}
          >
            {displayVal}
          </span>
        )
      })}
    </div>
  )
}

export default memo(PiiHeatmapPreview)

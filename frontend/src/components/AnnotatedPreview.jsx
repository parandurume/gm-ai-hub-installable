/** 인라인 어노테이션 미리보기 — 텍스트 위에 색상 밑줄 하이라이트 */

import { buildSegments, maskPartial } from '../utils/textSegments'

const TYPE_CLASS = {
  date: 'annotation-date',
  pii: 'annotation-pii',
  budget: 'annotation-budget',
}

export default function AnnotatedPreview({ text, annotations = [], onAnnotationClick }) {
  if (!text) return null

  const segments = buildSegments(text, annotations)

  return (
    <div className="preview-body annotated-preview" style={{ whiteSpace: 'pre-wrap' }}>
      {segments.map((seg, i) => {
        if (!seg.marker) {
          return <span key={i}>{seg.text}</span>
        }

        const cls = TYPE_CLASS[seg.marker.type] || 'annotation'
        const displayText = seg.marker.type === 'pii'
          ? maskPartial(seg.text)
          : seg.text

        return (
          <span
            key={i}
            className={`annotation ${cls}`}
            title={seg.marker.message || seg.marker.subtype}
            onClick={() => onAnnotationClick?.(seg.marker, i)}
            style={{ cursor: onAnnotationClick ? 'pointer' : undefined }}
          >
            {displayText}
          </span>
        )
      })}
    </div>
  )
}

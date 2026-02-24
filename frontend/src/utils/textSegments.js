/** 텍스트 세그먼트 유틸 — 마커(annotations/findings) 기반 하이라이트 분할 */

/**
 * markers: [{start, end, type, ...rest}] — 반드시 정렬된 상태일 것
 * 반환: [{text, marker?}] 배열
 */
export function buildSegments(text, markers = []) {
  if (!markers.length) return [{ text }]

  const sorted = [...markers].sort((a, b) => a.start - b.start)
  const segments = []
  let cursor = 0

  for (const m of sorted) {
    const start = Math.max(m.start, cursor)
    const end = Math.min(m.end, text.length)
    if (start >= end) continue

    // plain text before this marker
    if (cursor < start) {
      segments.push({ text: text.slice(cursor, start) })
    }
    segments.push({ text: text.slice(start, end), marker: m })
    cursor = end
  }

  // trailing plain text
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) })
  }

  return segments
}

/** 부분 마스킹: 앞 2자 + 중간 '●' + 끝 2자 (4자 이하면 전부 마스킹) */
export function maskPartial(text) {
  if (!text || text.length <= 4) return '●'.repeat(text?.length || 0)
  return text.slice(0, 2) + '●'.repeat(text.length - 4) + text.slice(-2)
}

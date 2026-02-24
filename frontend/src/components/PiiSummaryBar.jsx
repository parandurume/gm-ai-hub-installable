/** PII 스캔 요약 바 — PII 유형별 컬러 칩 + 총 카운트 */

const PII_COLORS = {
  '주민등록번호': { bg: 'rgba(192,57,43,0.12)', color: '#c0392b' },
  '전화번호':     { bg: 'rgba(41,128,185,0.12)', color: '#2980b9' },
  '이메일':       { bg: 'rgba(142,68,173,0.12)', color: '#8e44ad' },
  '주소':         { bg: 'rgba(39,174,96,0.12)',  color: '#27ae60' },
  '계좌번호':     { bg: 'rgba(211,84,0,0.12)',   color: '#d35400' },
  '여권번호':     { bg: 'rgba(22,160,133,0.12)', color: '#16a085' },
  '운전면허번호': { bg: 'rgba(44,62,80,0.12)',   color: '#2c3e50' },
}

function getColor(type) {
  return PII_COLORS[type] || { bg: 'rgba(0,0,0,0.08)', color: '#555' }
}

export default function PiiSummaryBar({ scanResult, loading }) {
  if (loading) {
    return (
      <div className="pii-summary-bar">
        <span className="pii-type-chip" style={{ background: 'var(--paper2)' }}>스캔 중...</span>
      </div>
    )
  }

  if (!scanResult) return null

  const { findings = [], total_found = 0 } = scanResult

  // 유형별 카운트
  const typeCounts = {}
  for (const f of findings) {
    typeCounts[f.type] = (typeCounts[f.type] || 0) + 1
  }

  return (
    <div className="pii-summary-bar">
      <span className={`pii-total-chip ${total_found > 0 ? 'has-pii' : 'clean'}`}>
        {total_found > 0 ? `${total_found}건 발견` : 'PII 없음'}
      </span>
      {Object.entries(typeCounts).map(([type, count]) => {
        const c = getColor(type)
        return (
          <span
            key={type}
            className="pii-type-chip"
            style={{ background: c.bg, color: c.color }}
          >
            {type} {count}
          </span>
        )
      })}
    </div>
  )
}

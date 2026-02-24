/** 검증 요약 바 — DateGuard / PII / Budget 통과/실패 칩 */

export default function GuardSummaryBar({ dateGuard, pii, budget, loading }) {
  if (loading) {
    return (
      <div className="guard-summary-bar">
        <span className="guard-chip loading">검증 중...</span>
      </div>
    )
  }

  if (!dateGuard && !pii) return null

  return (
    <div className="guard-summary-bar">
      {dateGuard && (
        <span className={`guard-chip ${dateGuard.passed ? 'pass' : 'fail'}`}>
          날짜 {dateGuard.passed ? '통과' : `오류 (${dateGuard.stale_years?.length || 0}건)`}
        </span>
      )}
      {pii && (
        <span className={`guard-chip ${pii.passed ? 'pass' : 'fail'}`}>
          PII {pii.passed ? '없음' : `${pii.total_found}건 발견`}
        </span>
      )}
      {budget && (
        <span className={`guard-chip ${budget.valid ? 'pass' : 'fail'}`}>
          예산 {budget.valid ? '적정' : `이슈 ${budget.issues?.length || 0}건`}
        </span>
      )}
    </div>
  )
}

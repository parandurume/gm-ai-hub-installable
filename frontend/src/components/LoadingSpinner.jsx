export default function LoadingSpinner({ text = '로딩 중...' }) {
  return (
    <div className="loading-overlay">
      <span className="spinner" />
      <span style={{ marginLeft: 8 }}>{text}</span>
    </div>
  )
}

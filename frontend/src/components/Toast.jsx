/** Toast 컴포넌트 (useToast 훅과 함께 사용) */
export default function Toast({ message, type = 'info' }) {
  return <div className={`toast toast-${type}`}>{message}</div>
}

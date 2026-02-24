import Modal from './Modal'

/**
 * Reusable confirmation dialog.
 *
 * Props:
 *   open        boolean — whether to show the dialog
 *   title       string  — dialog heading
 *   message     string  — body text
 *   confirmLabel string — confirm button label (default: '확인')
 *   cancelLabel  string — cancel button label  (default: '취소')
 *   danger      boolean — use red confirm button (default: false)
 *   onConfirm   () => void
 *   onCancel    () => void
 */
export default function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = '확인',
  cancelLabel = '취소',
  danger = false,
  onConfirm,
  onCancel,
}) {
  if (!open) return null
  return (
    <Modal
      title={title}
      onClose={onCancel}
      actions={
        <>
          <button className="btn btn-secondary" onClick={onCancel}>{cancelLabel}</button>
          <button className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </>
      }
    >
      <p style={{ padding: '12px 0', color: 'var(--ink2)', lineHeight: 1.6 }}>{message}</p>
    </Modal>
  )
}

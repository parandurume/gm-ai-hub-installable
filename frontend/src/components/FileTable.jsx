import { memo } from 'react'
import { getFileIcon } from '../utils/fileIcons'
import { formatSize } from '../utils/date'

/* rerender-memo: FileTable renders many rows; memo prevents re-render
   when parent state changes that don't affect files/selected/onSelect. */
export default memo(function FileTable({ files, selected, onSelect }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th style={{ width: 36 }}></th>
          <th>파일명</th>
          <th>크기</th>
          <th>수정일</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {files.map(f => (
          <tr
            key={f.path}
            className={`file-row ${selected === f.path ? 'active' : ''}`}
            onClick={() => onSelect(f.path)}
          >
            <td><span className="file-icon">{getFileIcon(f.ext)}</span></td>
            <td>{f.filename}</td>
            <td>{formatSize(f.size_bytes)}</td>
            <td>{f.modified_at ? new Date(f.modified_at * 1000).toLocaleDateString('ko') : ''}</td>
            <td>
              <button className="btn btn-sm btn-secondary" onClick={e => { e.stopPropagation(); onSelect(f.path) }}>
                열기
              </button>
            </td>
          </tr>
        ))}
        {files.length === 0 && (
          <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--ink3)' }}>파일 없음</td></tr>
        )}
      </tbody>
    </table>
  )
})

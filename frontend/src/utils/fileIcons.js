/** 파일 아이콘 매핑 */

const ICONS = {
  hwpx: '\uD83D\uDCD7',
  hwp:  '\uD83D\uDCD8',
  pdf:  '\uD83D\uDCD5',
  docx: '\uD83D\uDCC4',
  xlsx: '\uD83D\uDCCA',
  txt:  '\uD83D\uDCC3',
  md:   '\uD83D\uDCDD',
}

export function getFileIcon(ext) {
  return ICONS[ext?.toLowerCase()] || '\uD83D\uDCC1'
}

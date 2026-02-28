/** 사용자 가이드 투어 훅 + Provider */
import { createContext, useContext, useState, useCallback } from 'react'

const TourContext = createContext({
  active: false,
  step: 0,
  startTour: () => {},
  endTour: () => {},
  nextStep: () => {},
  prevStep: () => {},
  isCompleted: false,
})

const LS_KEY = 'tour_completed'

const TOUR_STEPS = [
  {
    id: 'welcome',
    title: 'GM-AI-Hub에 오신 것을 환영합니다!',
    description: '이 가이드에서는 GM-AI-Hub의 주요 기능을 안내합니다.\n모든 AI 처리는 이 컴퓨터에서만 실행되며, 외부로 데이터가 전송되지 않습니다.',
    icon: '\uD83C\uDFE0',
    path: '/',
  },
  {
    id: 'dashboard',
    title: '대시보드',
    description: '대시보드에서는 시스템 상태, 최근 문서, 주요 기능 바로가기를 한눈에 확인할 수 있습니다.\n카드를 클릭하면 해당 기능 페이지로 이동합니다.',
    icon: '\uD83D\uDCCA',
    path: '/',
  },
  {
    id: 'draft',
    title: '기안문 작성',
    description: '공문서 기안문을 AI가 자동으로 작성합니다.\n문서 종류, 제목, 지시사항을 입력하면 AI가 공문서 형식에 맞는 본문을 생성하고 HWPX 파일로 저장합니다.',
    icon: '\u270D\uFE0F',
    path: '/draft',
  },
  {
    id: 'meeting',
    title: '회의록 작성',
    description: '회의 내용을 입력하거나 음성을 녹음하면, AI가 공문서 형식의 회의록을 자동 생성합니다.\n마이크 녹음 또는 오디오 파일 업로드로 음성 인식(STT)도 지원합니다.',
    icon: '\uD83D\uDCCB',
    path: '/meeting',
  },
  {
    id: 'chat',
    title: 'AI 채팅',
    description: '로컬 AI와 자유롭게 대화할 수 있습니다.\n공문서 작성, 법령 해석, 업무 관련 질문 등 다양한 용도로 활용하세요.\n대화 내용은 세션별로 자동 저장됩니다.',
    icon: '\uD83E\uDD16',
    path: '/chat',
  },
  {
    id: 'complaint',
    title: '민원 답변',
    description: '민원 내용을 입력하면 AI가 민원 유형을 자동 분류하고, 공문서 형식에 맞는 답변 초안을 생성합니다.',
    icon: '\uD83D\uDCE8',
    path: '/complaint',
  },
  {
    id: 'search',
    title: '문서 검색',
    description: '작업 폴더에 저장된 HWPX, PDF, DOCX, TXT 파일을 키워드 또는 AI 의미 검색으로 찾을 수 있습니다.\n하이브리드 모드가 가장 정확합니다.',
    icon: '\uD83D\uDD0D',
    path: '/search',
  },
  {
    id: 'settings',
    title: '설정',
    description: 'Ollama 연결, 작업 폴더, AI 모델 관리, 프롬프트 최적화 등을 설정할 수 있습니다.\n부서명과 담당자 이름을 설정하면 문서 작성 시 자동으로 입력됩니다.',
    icon: '\u2699\uFE0F',
    path: '/settings',
  },
  {
    id: 'complete',
    title: '가이드 완료!',
    description: '주요 기능을 모두 확인했습니다.\n언제든 상단의 ? 버튼으로 이 가이드를 다시 볼 수 있습니다.\n즐거운 업무 되세요!',
    icon: '\u2705',
    path: '/',
  },
]

export function TourProvider({ children }) {
  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)

  const startTour = useCallback(() => {
    setStep(0)
    setActive(true)
  }, [])

  const endTour = useCallback((markComplete = true) => {
    setActive(false)
    setStep(0)
    if (markComplete) {
      localStorage.setItem(LS_KEY, 'true')
    }
  }, [])

  const nextStep = useCallback(() => {
    setStep(s => Math.min(s + 1, TOUR_STEPS.length - 1))
  }, [])

  const prevStep = useCallback(() => {
    setStep(s => Math.max(0, s - 1))
  }, [])

  return (
    <TourContext.Provider value={{
      active,
      step,
      steps: TOUR_STEPS,
      startTour,
      endTour,
      nextStep,
      prevStep,
      isCompleted: localStorage.getItem(LS_KEY) === 'true',
      totalSteps: TOUR_STEPS.length,
    }}>
      {children}
    </TourContext.Provider>
  )
}

export function useTour() {
  return useContext(TourContext)
}

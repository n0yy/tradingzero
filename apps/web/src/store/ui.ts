import { create } from 'zustand'

type TimeMode = 'utc' | 'local'

type UIState = {
  timeMode: TimeMode
  toggleTimeMode: () => void
}

export const useUIStore = create<UIState>((set) => ({
  timeMode: 'utc',
  toggleTimeMode: () => set((state) => ({ timeMode: state.timeMode === 'utc' ? 'local' : 'utc' })),
}))

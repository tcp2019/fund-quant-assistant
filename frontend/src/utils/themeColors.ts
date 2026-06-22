import { chartColor } from './chartColors'

const THEME_COLOR_INDEX: Record<string, number> = {
  storage_semiconductor: 0,
  cpo_optics: 1,
  ai_compute: 2,
  new_energy: 3,
  healthcare: 4,
  consumer: 5,
  dividend: 6,
  gold: 7,
  qdii: 8,
}

export function themeColor(themeId: string): string {
  const index = THEME_COLOR_INDEX[themeId] ?? themeId.length
  return chartColor(index)
}

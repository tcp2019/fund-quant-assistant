import type { HoldingTheme } from '../types'
import { themeColor } from '../utils/themeColors'

interface ThemeTagsProps {
  themes: HoldingTheme[]
}

export default function ThemeTags({ themes }: ThemeTagsProps) {
  if (themes.length === 0) {
    return null
  }

  return (
    <div className="mt-1.5 flex flex-wrap gap-1">
      {themes.map((item) => {
        const color = themeColor(item.theme)
        return (
          <span
            key={item.theme}
            className="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium leading-none"
            style={{
              color,
              backgroundColor: `${color}18`,
              border: `1px solid ${color}40`,
            }}
          >
            {item.label}
          </span>
        )
      })}
    </div>
  )
}

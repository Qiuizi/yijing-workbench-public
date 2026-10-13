import type { DivinationLine } from './types'

export interface VisualLine {
  position: number
  yinYang: '阴' | '阳'
  changing: boolean
  value: number
  coins: number[] | null
}

/** Presentation ordering only: the calculation and stored array stay bottom-to-top. */
export function toVisualLines(lines: DivinationLine[]): VisualLine[] {
  return [...lines]
    .sort((a, b) => b.position - a.position)
    .map(({ position, yin_yang, changing, value, coins }) => ({
      position,
      yinYang: yin_yang,
      changing,
      value,
      coins,
    }))
}


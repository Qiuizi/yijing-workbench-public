import { describe, expect, it } from 'vitest'
import { toVisualLines } from './lineView'
import type { DivinationLine } from './types'

describe('toVisualLines', () => {
  it('renders top-to-bottom while keeping the source lines unchanged', () => {
    const lines: DivinationLine[] = [
      { position: 1, value: 9, yin_yang: '阳', changing: true, coins: [3, 3, 3] },
      { position: 2, value: 7, yin_yang: '阳', changing: false, coins: [2, 2, 3] },
      { position: 3, value: 8, yin_yang: '阴', changing: false, coins: [2, 3, 3] },
      { position: 4, value: 7, yin_yang: '阳', changing: false, coins: [3, 2, 2] },
      { position: 5, value: 8, yin_yang: '阴', changing: false, coins: [3, 2, 3] },
      { position: 6, value: 7, yin_yang: '阳', changing: false, coins: [2, 3, 2] },
    ]

    const view = toVisualLines(lines)

    expect(view.map((line) => line.position)).toEqual([6, 5, 4, 3, 2, 1])
    expect(view.at(-1)?.changing).toBe(true)
    expect(view.at(-1)?.coins).toEqual([3, 3, 3])
    expect(lines[0].position).toBe(1)
  })
})


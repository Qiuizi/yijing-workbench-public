import type { DivinationLine, Hexagram, SpecialLine } from './types'

/** Only original casts of six old yang/old yin lines activate these texts. */
export function specialLineForCast(
  hexagram: Hexagram,
  lines: readonly DivinationLine[],
): SpecialLine | null {
  const requiredValue = hexagram.wenwang_order === 1 ? 9 : hexagram.wenwang_order === 2 ? 6 : null
  const expectedName = hexagram.wenwang_order === 1 ? '用九' : hexagram.wenwang_order === 2 ? '用六' : null

  if (requiredValue === null || lines.length !== 6 || !lines.every((line) => line.value === requiredValue)) {
    return null
  }

  const specialLine = hexagram.special_line
  return specialLine?.name === expectedName ? specialLine : null
}

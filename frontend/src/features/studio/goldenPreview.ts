import type { Draft, GoldenOpeningCandidate, Scene } from './types'

export function goldenBodyScenes(draft: Draft): Scene[] {
  return draft.origin === 'golden-open' && draft.scenes[0]?.id === 'golden-open'
    ? draft.scenes.slice(1)
    : draft.scenes
}

export function goldenPreviewSegments(draft: Draft, candidate: GoldenOpeningCandidate) {
  return [
    { id: 'golden-open', start: candidate.start, end: candidate.end },
    ...goldenBodyScenes(draft).map(scene => ({ id: scene.id, start: scene.start, end: scene.end })),
  ]
}

type PlaybackRange = Pick<Scene, 'id' | 'start' | 'end'>

export function goldenTimelineOffset(segments: PlaybackRange[], sourceTime: number): number {
  let offset = 0
  for (const segment of segments) {
    const duration = segment.end - segment.start
    if (sourceTime < segment.end) return offset + Math.max(0, Math.min(sourceTime - segment.start, duration))
    offset += duration
  }
  return offset
}

export function goldenSourceAt(segments: PlaybackRange[], offset: number): { index: number; time: number } {
  let remaining = Math.max(0, offset)
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index]
    const duration = segment.end - segment.start
    if (remaining < duration || index === segments.length - 1) {
      return { index, time: segment.start + Math.min(remaining, duration) }
    }
    remaining -= duration
  }
  return { index: 0, time: 0 }
}

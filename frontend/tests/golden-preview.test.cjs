const { test } = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')
const { loadTs } = require('./load-ts.cjs')

const { goldenBodyScenes, goldenPreviewSegments, goldenTimelineOffset, goldenSourceAt } = loadTs(path.resolve(__dirname, '../src/features/studio/goldenPreview.ts'))
const scene = (id, start, end) => ({ id, start, end, label: id, evidence: '' })
const candidate = { id: 'golden-4-4', start: 20, end: 23, text: 'candidate', reason: '' }

test('joined preview plays the selected opening and then every body scene', () => {
  const draft = { origin: 'auto-content', scenes: [scene('body-1', 1, 5), scene('body-2', 8, 12)] }
  assert.deepEqual(JSON.parse(JSON.stringify(goldenPreviewSegments(draft, candidate))), [
    { id: 'golden-open', start: 20, end: 23 },
    { id: 'body-1', start: 1, end: 5 },
    { id: 'body-2', start: 8, end: 12 },
  ])
})

test('reselecting on a derived draft replaces the old opening in preview', () => {
  const draft = { origin: 'golden-open', scenes: [scene('golden-open', 1, 3), scene('body', 8, 12)] }
  assert.deepEqual(JSON.parse(JSON.stringify(goldenBodyScenes(draft).map(x => x.id))), ['body'])
  assert.deepEqual(JSON.parse(JSON.stringify(goldenPreviewSegments(draft, candidate).map(x => [x.id, x.start]))), [
    ['golden-open', 20], ['body', 8],
  ])
})

test('joined timeline maps playback and seeking across non-contiguous source ranges', () => {
  const segments = [scene('golden-open', 100, 102), scene('body', 200, 210)]
  assert.equal(goldenTimelineOffset(segments, 100), 0)
  assert.equal(goldenTimelineOffset(segments, 101), 1)
  assert.equal(goldenTimelineOffset(segments, 200), 2)
  assert.equal(goldenTimelineOffset(segments, 205), 7)
  assert.equal(goldenTimelineOffset(segments, 210), 12)
  assert.deepEqual(JSON.parse(JSON.stringify(goldenSourceAt(segments, 0))), { index: 0, time: 100 })
  assert.deepEqual(JSON.parse(JSON.stringify(goldenSourceAt(segments, 2))), { index: 1, time: 200 })
  assert.deepEqual(JSON.parse(JSON.stringify(goldenSourceAt(segments, 7))), { index: 1, time: 205 })
  assert.deepEqual(JSON.parse(JSON.stringify(goldenSourceAt(segments, 99))), { index: 1, time: 210 })
})

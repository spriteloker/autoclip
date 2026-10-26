import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Btn, Dialog } from '../../ui'
import { studioApi, errorText } from './api'
import type { Draft, GoldenOpeningCandidate } from './types'

export default function GoldenOpeningDialog({ projectId, draft, onClose, onCreated }: {
  projectId: string; draft: Draft; onClose: () => void; onCreated: (draft: Draft) => void
}) {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const previewRange = useRef<{ start: number; end: number } | null>(null)
  const [candidates, setCandidates] = useState<GoldenOpeningCandidate[]>([])
  const [selected, setSelected] = useState('')
  const [previewing, setPreviewing] = useState(false)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const current = candidates.find(item => item.id === selected)

  useEffect(() => {
    let active = true
    setBusy('analyze')
    setError('')
    studioApi.goldenOpeningAnalyze(projectId, draft).then(result => {
      if (!active) return
      setCandidates(result.candidates)
      setSelected(result.candidates[0]?.id || '')
    }).catch(reason => { if (active) setError(t(errorText(reason))) }).finally(() => {
      if (active) setBusy('')
    })
    return () => { active = false; videoRef.current?.pause() }
  }, [projectId, draft.id])

  const stopPreview = () => {
    videoRef.current?.pause()
    previewRange.current = null
    setPreviewing(false)
  }
  const choose = (id: string) => { stopPreview(); setSelected(id) }
  const startPreview = (candidate: GoldenOpeningCandidate) => {
    const video = videoRef.current
    if (!video) return
    setSelected(candidate.id)
    previewRange.current = { start: candidate.start, end: candidate.end }
    setError('')
    const play = () => {
      video.currentTime = candidate.start
      void video.play().then(() => setPreviewing(true)).catch(() => {
        setPreviewing(false)
        setError(t('原片无法播放时，可生成兼容预览；原片不变，不调用模型。'))
      })
    }
    if (video.readyState >= 1) play()
    else { video.load(); video.addEventListener('loadedmetadata', play, { once: true }) }
  }
  const loopPreview = () => {
    const video = videoRef.current
    const range = previewRange.current
    if (!video || !previewing || !range || video.currentTime + .04 < range.end) return
    video.currentTime = range.start
    void video.play().catch(() => {
      stopPreview()
      setError(t('原片无法播放时，可生成兼容预览；原片不变，不调用模型。'))
    })
  }
  const apply = async () => {
    if (!current) return
    stopPreview()
    setBusy('apply')
    setError('')
    try {
      const created = await studioApi.goldenOpeningApply(projectId, draft, current)
      onCreated(created)
    } catch (reason) {
      setError(t(errorText(reason)))
      setBusy('')
    }
  }

  return <Dialog open onClose={onClose} title={t('黄金三秒片头')} description={t('三个候选可反复切换并分别预览片头；创建派生草稿，原候选保持不变。')}
    footer={<div className="studio-actions"><Btn disabled={!!busy} onClick={onClose}>{t('取消')}</Btn><Btn variant="cta" disabled={!selected || !!busy} loading={busy === 'apply'} onClick={apply}>{t('创建派生草稿')}</Btn></div>}>
    <video ref={videoRef} src={studioApi.source(projectId)} preload="auto" onTimeUpdate={loopPreview} onEnded={stopPreview}
      onClick={() => previewing ? stopPreview() : current && startPreview(current)}
      style={{ width: '100%', maxHeight: 260, background: '#111', borderRadius: 8, cursor: 'pointer' }} />
    <div className="studio-actions" style={{ marginTop: 8 }}>
      <Btn disabled={!current || !!busy} onClick={() => previewing ? stopPreview() : current && startPreview(current)}>{t(previewing ? '停止片头预览' : '播放本段片头')}</Btn>
      <span className="studio-muted">{t('此处只循环播放选中的几秒片头；创建后在编辑器播放完整拼接。')}</span>
    </div>
    {busy === 'analyze' && <p className="studio-muted">{t('正在挑选适合片头的完整金句…')}</p>}
    {error && <p className="studio-error" role="alert">{error}</p>}
    {!busy && !candidates.length && !error && <p className="studio-muted">{t('没有找到不超过 8 秒且语境完整的候选片段，请换一段素材。')}</p>}
    {candidates.map(candidate => <label key={candidate.id} className="studio-source-row" style={{ cursor: 'pointer' }}>
      <input type="radio" name="golden-opening" value={candidate.id} checked={selected === candidate.id} onChange={() => choose(candidate.id)} disabled={!!busy} />
      <div><b>{t('约 {{seconds}} 秒', { seconds: (candidate.end - candidate.start).toFixed(1) })}</b><p>{candidate.text}</p><p className="studio-muted">{candidate.reason}</p></div>
    </label>)}
  </Dialog>
}

import { getActivity } from '../../services/activities'
import type { ActivityDetail } from '../../types/api'
import { locale, t } from '../../utils/i18n'

function fmtDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day} ${h}:${min}`
}

Page({
  data: {
    lang: locale.get(),
    activity: null as ActivityDetail | null,
    loading: true,
    drawing: false,
    posterPath: '',
    title: '',
    saveText: '',
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    this.setData({
      lang: locale.get(),
      title: t('poster.title'),
      saveText: t('poster.save'),
    })
    wx.setNavigationBarTitle({ title: t('poster.title') })
    if (Number.isFinite(id)) this.load(id)
  },

  async load(id: number) {
    this.setData({ loading: true })
    try {
      const activity = await getActivity(id)
      this.setData({ activity })
      setTimeout(() => this.drawPoster(), 100)
    } finally {
      this.setData({ loading: false })
    }
  },

  drawRoundRect(ctx: WechatMiniprogram.CanvasContext, x: number, y: number, w: number, h: number, r: number) {
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.lineTo(x + w - r, y)
    ctx.quadraticCurveTo(x + w, y, x + w, y + r)
    ctx.lineTo(x + w, y + h - r)
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
    ctx.lineTo(x + r, y + h)
    ctx.quadraticCurveTo(x, y + h, x, y + h - r)
    ctx.lineTo(x, y + r)
    ctx.quadraticCurveTo(x, y, x + r, y)
    ctx.closePath()
  },

  wrapText(ctx: WechatMiniprogram.CanvasContext, text: string, x: number, y: number, maxWidth: number, lineHeight: number, maxLines: number) {
    let line = ''
    let lines = 0
    for (let i = 0; i < text.length; i += 1) {
      const testLine = line + text[i]
      if (ctx.measureText(testLine).width > maxWidth && line) {
        ctx.fillText(line, x, y)
        y += lineHeight
        line = text[i]
        lines += 1
        if (lines >= maxLines - 1) break
      } else {
        line = testLine
      }
    }
    if (line && lines < maxLines) ctx.fillText(line, x, y)
  },

  drawPoster() {
    const activity = this.data.activity
    if (!activity) return
    this.setData({ drawing: true })
    const ctx = wx.createCanvasContext('posterCanvas')
    ctx.setFillStyle('#f7f3ef')
    ctx.fillRect(0, 0, 375, 667)

    ctx.setFillStyle('#ffffff')
    this.drawRoundRect(ctx, 18, 18, 339, 631, 18)
    ctx.fill()

    ctx.drawImage('/assets/campus-hero.jpg', 18, 18, 339, 190)
    ctx.setFillStyle('rgba(8, 21, 42, 0.54)')
    ctx.fillRect(18, 134, 339, 74)
    ctx.setFillStyle('#ffffff')
    ctx.setFontSize(18)
    ctx.fillText(activity.organizer || '校友商会', 38, 172)

    ctx.setFillStyle('#101828')
    ctx.setFontSize(24)
    this.wrapText(ctx, activity.title, 38, 252, 299, 32, 2)

    ctx.setFillStyle('#7d6f68')
    ctx.setFontSize(15)
    ctx.fillText(`${t('poster.time')}: ${fmtDate(activity.start_at)}`, 38, 336)
    ctx.fillText(`${t('poster.place')}: ${activity.location}`, 38, 366)
    ctx.fillText(`${t('poster.signup')}: ${activity.signup_count} ${t('poster.people')}`, 38, 396)

    ctx.setFillStyle('#b92722')
    this.drawRoundRect(ctx, 38, 436, 180, 40, 20)
    ctx.fill()
    ctx.setFillStyle('#ffffff')
    ctx.setFontSize(16)
    ctx.fillText(t('poster.cta'), 66, 462)

    ctx.setFillStyle('#fff4e1')
    this.drawRoundRect(ctx, 245, 438, 82, 82, 10)
    ctx.fill()
    ctx.setFillStyle('#b92722')
    ctx.setFontSize(13)
    ctx.fillText('MINI', 270, 475)
    ctx.fillText('CODE', 268, 496)

    ctx.setFillStyle('#7d6f68')
    ctx.setFontSize(12)
    ctx.fillText(t('poster.scan_hint'), 38, 566)
    ctx.fillText('校友商会 · 同窗聚力 · 商通全球', 38, 594)

    ctx.draw(false, () => {
      wx.canvasToTempFilePath({
        canvasId: 'posterCanvas',
        success: (res) => this.setData({ posterPath: res.tempFilePath }),
        complete: () => this.setData({ drawing: false }),
      })
    })
  },

  async onSave() {
    const path = this.data.posterPath
    if (!path) {
      this.drawPoster()
      return
    }
    try {
      await wx.saveImageToPhotosAlbum({ filePath: path })
      wx.showToast({ title: t('poster.saved'), icon: 'success' })
    } catch {
      wx.showToast({ title: t('poster.save_failed'), icon: 'none' })
    }
  },
})

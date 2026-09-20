import { adminAiChat } from '../../services/ai'
import { locale, t } from '../../utils/i18n'

Page({
  data: {
    lang: locale.get(),
    message: '',
    answer: '',
    loading: false,
    copy: {
      title: '',
      placeholder: '',
      send: '',
      empty: '',
    },
  },

  onShow() {
    this.setData({
      lang: locale.get(),
      copy: {
        title: t('ai.title'),
        placeholder: t('ai.placeholder'),
        send: t('ai.send'),
        empty: t('ai.empty'),
      },
    })
    wx.setNavigationBarTitle({ title: t('ai.title') })
  },

  onInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ message: e.detail.value })
  },

  async onSend() {
    const message = this.data.message.trim()
    if (!message || this.data.loading) return
    this.setData({ loading: true, answer: '' })
    try {
      const res = await adminAiChat(message)
      this.setData({ answer: res.answer })
    } catch (e) {
      this.setData({ answer: (e as Error).message || t('common.fail') })
    } finally {
      this.setData({ loading: false })
    }
  },
})

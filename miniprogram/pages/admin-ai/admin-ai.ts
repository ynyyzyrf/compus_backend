import { adminAiChat } from '../../services/ai'
import { locale, t } from '../../utils/i18n'

type ChatMessage = {
  id: number
  role: 'assistant' | 'user'
  content: string
}

let messageSeq = 0

Page({
  data: {
    lang: locale.get(),
    message: '',
    messages: [] as ChatMessage[],
    quickQuestions: [] as string[],
    scrollTop: 0,
    loading: false,
    copy: {
      title: '',
      placeholder: '',
      send: '',
      greeting: '',
      sending: '',
    },
  },

  onShow() {
    const copy = {
      title: t('ai.title'),
      placeholder: t('ai.placeholder'),
      send: t('ai.send'),
      greeting: t('ai.greeting'),
      sending: t('ai.sending'),
    }
    const nextData: Record<string, unknown> = {
      lang: locale.get(),
      copy,
      quickQuestions: [
        t('ai.quick.activity_signup'),
        t('ai.quick.active_department'),
        t('ai.quick.no_checkin'),
      ],
    }
    if (!this.data.messages.length) {
      nextData.messages = [this.createMessage('assistant', copy.greeting)]
    }
    this.setData({
      ...nextData,
    })
    wx.setNavigationBarTitle({ title: t('ai.title') })
  },

  onInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ message: e.detail.value })
  },

  onQuickAsk(e: WechatMiniprogram.CustomEvent<{ text: string }>) {
    const text = e.currentTarget.dataset.text || ''
    this.sendQuestion(text)
  },

  onSend() {
    this.sendQuestion(this.data.message)
  },

  createMessage(role: ChatMessage['role'], content: string): ChatMessage {
    messageSeq += 1
    return { id: messageSeq, role, content }
  },

  scrollToBottom() {
    wx.nextTick(() => {
      this.setData({ scrollTop: messageSeq * 10000 })
    })
  },

  async sendQuestion(rawMessage: string) {
    const message = rawMessage.trim()
    if (!message || this.data.loading) return

    let messages = [...this.data.messages, this.createMessage('user', message)]
    this.setData({ messages, message: '', loading: true })
    this.scrollToBottom()

    try {
      const res = await adminAiChat(message)
      messages = [...messages, this.createMessage('assistant', res.answer)]
    } catch (e) {
      messages = [...messages, this.createMessage('assistant', (e as Error).message || t('common.fail'))]
    } finally {
      this.setData({ messages, loading: false })
      this.scrollToBottom()
    }
  },
})

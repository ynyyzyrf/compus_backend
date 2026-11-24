import { listFriendMessages, markFriendMessagesRead, sendFriendMessage } from '../../services/connections'
import type { FriendMessage } from '../../services/connections'
import { session } from '../../utils/session'

type MessageView = FriendMessage & { own: boolean; timeText: string }

function toView(message: FriendMessage, userId?: number): MessageView {
  return { ...message, own: message.sender_id === userId, timeText: new Date(message.created_at).toLocaleString() }
}

Page({
  data: {
    peerId: 0,
    messages: [] as MessageView[],
    draft: '',
    sending: false,
    loading: false,
    ready: false,
    hasMore: false,
    scrollTarget: '',
    error: '',
    pending: null as { text: string; clientId: string } | null,
  },

  onLoad(options: Record<string, string | undefined>) {
    const peerId = Number(options.id)
    if (Number.isSafeInteger(peerId) && peerId > 0) this.setData({ peerId })
    else this.setData({ error: '好友不存在' })
  },
  onShow() { if (this.data.peerId) void this.loadLatest() },
  async loadLatest() {
    await this.load()
  },
  async loadEarlier() {
    if (this.data.hasMore) await this.load(this.data.messages[0]?.id)
  },
  async load(beforeId?: number) {
    if (this.data.loading || !this.data.peerId) return
    const { peerId } = this.data
    this.setData({ loading: true, error: '' })
    try {
      const page = await listFriendMessages(peerId, beforeId)
      const items = page.items.map(item => toView(item, session.getUser()?.id))
      const messages = beforeId ? [...items, ...this.data.messages] : items
      const anchor = beforeId || messages[messages.length - 1]?.id
      this.setData({ messages, ready: true, hasMore: page.has_more, scrollTarget: anchor ? `message-${anchor}` : '' })
      wx.setNavigationBarTitle({ title: page.peer_name })
      const latestIncoming = items.slice().reverse().find(item => !item.own)
      if (!beforeId && latestIncoming) await markFriendMessagesRead(peerId, latestIncoming.id).catch(() => undefined)
    } catch (error) {
      this.setData({ error: (error as Error).message || '暂时无法加载留言' })
    } finally {
      this.setData({ loading: false })
    }
  },
  onDraft(e: WechatMiniprogram.Input) { this.setData({ draft: e.detail.value }) },
  async send() {
    const { peerId, sending, ready, draft, pending } = this.data
    const value = draft.trim()
    if (!ready || sending || this.data.loading || !value) return
    const clientId = pending?.text === value ? pending.clientId : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
    this.setData({ sending: true, pending: { text: value, clientId } })
    try {
      const response = await sendFriendMessage(peerId, value, clientId)
      const items = this.data.messages.filter(item => item.id !== response.id)
      items.push(toView(response, session.getUser()?.id))
      this.setData({ messages: items, draft: this.data.draft === draft ? '' : this.data.draft,
        pending: null, scrollTarget: `message-${response.id}` })
    } catch (error) {
      wx.showToast({ title: (error as Error).message || '发送失败，请重试', icon: 'none' })
    } finally {
      this.setData({ sending: false })
    }
  },
})

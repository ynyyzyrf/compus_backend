import { ensureLogin, goLogin } from '../../services/auth'
import { listConnections, markRequestsRead, respondToRequest, shareWechat } from '../../services/connections'
import type { ConnectionItem } from '../../services/connections'
import { session } from '../../utils/session'
import { requestAlumniContact } from '../../utils/connection-actions'

interface RequestView extends ConnectionItem { statusLabel: string }

function requestLabel(item: ConnectionItem) {
  if (item.status === 'declined') return item.incoming ? '已拒绝' : '对方已拒绝'
  return item.incoming ? '待处理' : '等待对方处理'
}

Page({
  data: {
    tab: 'requests',
    requests: [] as RequestView[],
    friends: [] as ConnectionItem[],
    loading: true,
    error: '',
    busyId: 0,
    unreadMessages: 0,
  },
  onLoad(opts: Record<string, string | undefined>) {
    if (opts.tab === 'friends') this.setData({ tab: 'friends' })
  },
  onShow() { this.load() },
  async load() {
    const user = await ensureLogin().catch(() => null)
    if (!user || session.isGuest()) { goLogin(); return }
    this.setData({ loading: true, error: '' })
    try {
      const items = await listConnections()
      this.setData({
        requests: items.filter(item => item.status !== 'accepted').map(item => ({
          ...item, statusLabel: requestLabel(item),
        })),
        friends: items.filter(item => item.status === 'accepted'),
        unreadMessages: items.reduce((total, item) => total + (item.unread_messages || 0), 0),
      })
      if (this.data.tab === 'requests') await this.readVisible()
    } catch (error) {
      this.setData({ error: (error as Error).message || '好友资料载入失败' })
    } finally {
      this.setData({ loading: false })
    }
  },
  async readVisible() {
    const ids = this.data.requests.filter(item => item.unread).map(item => item.peer_id)
    for (let i = 0; i < ids.length; i += 100) {
      await markRequestsRead(ids.slice(i, i + 100)).catch(() => undefined)
    }
  },
  changeTab(e: WechatMiniprogram.BaseEvent) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ tab })
    if (tab === 'requests') this.readVisible()
  },
  async respond(e: WechatMiniprogram.BaseEvent) {
    const { id, action } = e.currentTarget.dataset
    if (this.data.busyId || (action !== 'accept' && action !== 'decline')) return
    this.setData({ busyId: Number(id) })
    try {
      await respondToRequest(Number(id), action)
      if (action === 'accept') this.setData({ tab: 'friends' })
      await this.load()
    } catch (error) {
      wx.showModal({ title: '处理失败', content: (error as Error).message || '请稍后重试', showCancel: false })
    } finally {
      this.setData({ busyId: 0 })
    }
  },
  async retryRequest(e: WechatMiniprogram.BaseEvent) {
    if (this.data.busyId) return
    const item = this.data.requests.find(request => request.peer_id === Number(e.currentTarget.dataset.id))
    if (!item || item.incoming || item.status !== 'declined') return
    this.setData({ busyId: item.peer_id })
    try {
      if (await requestAlumniContact(item.peer_id, item.name)) await this.load()
    } finally {
      this.setData({ busyId: 0 })
    }
  },
  toggleShare(e: WechatMiniprogram.BaseEvent) {
    const friend = this.data.friends.find(item => item.peer_id === Number(e.currentTarget.dataset.id))
    if (!friend || this.data.busyId) return
    const share = !friend.shares_wechat
    wx.showModal({
      title: share ? '分享我的微信号' : '取消分享微信号',
      content: share ? `允许${friend.name}在好友列表中查看你名片上的微信号。` : `取消后，${friend.name}的好友列表将隐藏你的微信号。`,
      success: async result => {
        if (!result.confirm) return
        this.setData({ busyId: friend.peer_id })
        try {
          await shareWechat(friend.peer_id, share)
          await this.load()
        } catch (error) {
          wx.showModal({ title: '操作失败', content: (error as Error).message || '请稍后重试', showCancel: false })
        } finally {
          this.setData({ busyId: 0 })
        }
      },
    })
  },
  copyWechat(e: WechatMiniprogram.BaseEvent) {
    const value = String(e.currentTarget.dataset.value || '')
    if (value) wx.setClipboardData({ data: value })
  },
  openFriendCard(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (id > 0) wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${id}` })
  },
  openMessages(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (id > 0) wx.navigateTo({ url: `/pages/friend-messages/friend-messages?id=${id}` })
  },
})

import { sendConnectionRequest } from '../services/connections'

export function requestAlumniContact(id: number, name: string) {
  wx.showModal({
    title: `添加${name}为好友`,
    editable: true,
    placeholderText: '写一句自我介绍（选填，最多 120 字）',
    confirmText: '发送申请',
    success: async result => {
      if (!result.confirm) return
      const message = (result.content || '').trim()
      if (message.length > 120) {
        wx.showToast({ title: '留言最多 120 字', icon: 'none' })
        return
      }
      try {
        await sendConnectionRequest(id, message)
        wx.showToast({ title: '好友申请已发送', icon: 'success' })
      } catch (error) {
        wx.showModal({ title: '发送失败', content: (error as Error).message || '请稍后重试', showCancel: false })
      }
    },
  })
}

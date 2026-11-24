const audiences = ['private', 'friends', 'classmates'] as const

interface VisibilityComponent {
  setData(data: { selection: Record<string, string> }): void
  triggerEvent(name: string, data: { key: string; value: typeof audiences[number] }): void
}

Component({
  properties: {
    basic: { type: String, value: 'classmates' },
    contact: { type: String, value: 'private' },
    details: { type: String, value: 'private' },
  },
  data: {
    options: ['仅自己', '好友', '同班同学和好友'],
    indices: { private: 0, friends: 1, classmates: 2 },
    groups: [
      { key: 'basic_visibility', prop: 'basic', label: '基础资料' },
      { key: 'contact_visibility', prop: 'contact', label: '联系方式' },
      { key: 'details_visibility', prop: 'details', label: '详细资料' },
    ],
    selection: {} as Record<string, string>,
  },
  observers: {
    'basic,contact,details'(this: VisibilityComponent, basic: string, contact: string, details: string) {
      this.setData({ selection: { basic, contact, details } })
    },
  },
  methods: {
    change(this: VisibilityComponent, e: WechatMiniprogram.PickerChange) {
      const value = audiences[Number(e.detail.value)]
      if (value) this.triggerEvent('change', { key: e.currentTarget.dataset.key, value })
    },
  },
})

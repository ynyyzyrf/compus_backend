import { adminCreateRelay, adminUpdateRelay, getRelay } from '../../services/relays'
import type { RelayFieldPayload, RelayFieldType } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type FieldForm = RelayFieldPayload & { optionsText: string }

function defaultFields(): FieldForm[] {
  return [
    { label: t('profile.name'), field_type: 'text', required: true, sort_order: 1, optionsText: '' },
    { label: t('relays.demo.attend'), field_type: 'radio', required: true, sort_order: 2, optionsText: `${t('relays.demo.yes')}\n${t('relays.demo.no')}` },
  ]
}

function normalizeDeadline(value: string): string | null {
  const text = value.trim()
  if (!text) return null
  if (text.includes('T')) return text
  return text.length === 10 ? `${text}T23:59:59+08:00` : text.replace(' ', 'T') + '+08:00'
}

Page({
  data: {
    lang: locale.get(),
    id: 0,
    title: '',
    description: '',
    deadline: '',
    status: 'open' as 'open' | 'closed',
    fields: defaultFields(),
    saving: false,
    typeOptions: [
      { value: 'text', label: t('relays.type.text') },
      { value: 'textarea', label: t('relays.type.textarea') },
      { value: 'number', label: t('relays.type.number') },
      { value: 'radio', label: t('relays.type.radio') },
      { value: 'checkbox', label: t('relays.type.checkbox') },
      { value: 'date', label: t('relays.type.date') },
      { value: 'image', label: t('relays.type.image') },
    ],
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    this.setData({ lang: locale.get() })
    if (Number.isFinite(id) && id > 0) {
      this.setData({ id })
      this.load(id)
    }
  },

  async load(id: number) {
    const relay = await getRelay(id)
    this.setData({
      title: relay.title,
      description: relay.description || '',
      deadline: relay.deadline ? relay.deadline.slice(0, 16).replace('T', ' ') : '',
      status: relay.status,
      fields: relay.fields.map((field, index) => ({
        label: field.label,
        field_type: field.field_type,
        required: field.required,
        sort_order: field.sort_order || index + 1,
        optionsText: (field.options || []).join('\n'),
      })),
    })
  },

  onTitle(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ title: e.detail.value }) },
  onDesc(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ description: e.detail.value }) },
  onDeadline(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ deadline: e.detail.value }) },
  onStatusTap(e: WechatMiniprogram.BaseEvent) { this.setData({ status: e.currentTarget.dataset.status as 'open' | 'closed' }) },

  updateField(index: number, patch: Partial<FieldForm>) {
    const fields = this.data.fields.slice()
    if (!fields[index]) return
    fields[index] = { ...fields[index], ...patch }
    this.setData({ fields })
  },
  onFieldLabel(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.updateField(Number(e.currentTarget.dataset.index), { label: e.detail.value })
  },
  onFieldOptions(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.updateField(Number(e.currentTarget.dataset.index), { optionsText: e.detail.value })
  },
  onFieldType(e: WechatMiniprogram.BaseEvent) {
    this.updateField(Number(e.currentTarget.dataset.index), { field_type: e.currentTarget.dataset.type as RelayFieldType })
  },
  onRequired(e: WechatMiniprogram.BaseEvent) {
    const index = Number(e.currentTarget.dataset.index)
    this.updateField(index, { required: !this.data.fields[index]?.required })
  },
  onAddField() {
    this.setData({
      fields: this.data.fields.concat([{ label: '', field_type: 'text', required: false, sort_order: this.data.fields.length + 1, optionsText: '' }]),
    })
  },
  onRemoveField(e: WechatMiniprogram.BaseEvent) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ fields: this.data.fields.filter((_, i) => i !== index) })
  },

  buildPayload() {
    const title = this.data.title.trim()
    if (!title) {
      wx.showToast({ title: t('relays.validation.title'), icon: 'none' })
      return null
    }
    const fields = this.data.fields
      .map((field, index) => ({
        label: field.label.trim(),
        field_type: field.field_type,
        required: field.required,
        sort_order: index + 1,
        options: field.optionsText.split('\n').map((s) => s.trim()).filter(Boolean),
      }))
      .filter((field) => field.label)
    if (!fields.length) {
      wx.showToast({ title: t('relays.validation.field'), icon: 'none' })
      return null
    }
    return {
      title,
      description: this.data.description.trim() || null,
      deadline: normalizeDeadline(this.data.deadline),
      status: this.data.status,
      fields,
    }
  },

  async onSave() {
    const payload = this.buildPayload()
    if (!payload) return
    this.setData({ saving: true })
    try {
      if (this.data.id) await adminUpdateRelay(this.data.id, payload)
      else await adminCreateRelay(payload)
      wx.showToast({ title: t('common.saved'), icon: 'success' })
      setTimeout(() => wx.navigateBack(), 300)
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('common.fail'), icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})

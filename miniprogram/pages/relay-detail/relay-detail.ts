import { getRelay, submitRelayResponse } from '../../services/relays'
import type { RelayDetail, RelayField } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type OptionView = { label: string; selected: boolean }
type FieldView = RelayField & { value: string; optionsView: OptionView[] }

function fmt(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}-${M}-${D} ${h}:${m}`
}

function fieldViews(fields: RelayField[], response: Record<string, unknown> = {}): FieldView[] {
  return fields.map((field) => {
    const raw = response[field.label]
    const value = Array.isArray(raw) ? raw.join(',') : raw === undefined || raw === null ? '' : String(raw)
    const selected = Array.isArray(raw) ? raw.map(String) : value ? [value] : []
    return {
      ...field,
      value,
      optionsView: (field.options || []).map((label) => ({ label, selected: selected.includes(label) })),
    }
  })
}

Page({
  data: {
    lang: locale.get(),
    loading: true,
    submitting: false,
    relay: null as RelayDetail | null,
    deadlineText: '',
    statusText: '',
    fields: [] as FieldView[],
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (!Number.isFinite(id)) {
      this.setData({ loading: false })
      return
    }
    this.load(id)
  },

  async load(id: number) {
    this.setData({ loading: true })
    try {
      const relay = await getRelay(id)
      const myResponse = (relay.my_response || {}) as Record<string, unknown>
      this.setData({
        lang: locale.get(),
        relay,
        deadlineText: fmt(relay.deadline),
        statusText: t(`relays.status.${relay.status}`),
        fields: fieldViews(relay.fields, myResponse),
      })
      wx.setNavigationBarTitle({ title: relay.title.slice(0, 14) })
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('relays.load_failed'), icon: 'none' })
      this.setData({ relay: null })
    } finally {
      this.setData({ loading: false })
    }
  },

  onInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    const index = Number(e.currentTarget.dataset.index)
    const fields = this.data.fields.slice()
    if (!fields[index]) return
    fields[index] = { ...fields[index], value: e.detail.value }
    this.setData({ fields })
  },

  onOptionTap(e: WechatMiniprogram.BaseEvent) {
    const index = Number(e.currentTarget.dataset.index)
    const option = String(e.currentTarget.dataset.option || '')
    const field = this.data.fields[index]
    if (!field || !option) return
    const fields = this.data.fields.slice()
    if (field.field_type === 'radio') {
      fields[index] = {
        ...field,
        value: option,
        optionsView: field.optionsView.map((item) => ({ ...item, selected: item.label === option })),
      }
    } else {
      const selected = new Set(field.value ? field.value.split(',').filter(Boolean) : [])
      if (selected.has(option)) selected.delete(option)
      else selected.add(option)
      const values = Array.from(selected)
      fields[index] = {
        ...field,
        value: values.join(','),
        optionsView: field.optionsView.map((item) => ({ ...item, selected: selected.has(item.label) })),
      }
    }
    this.setData({ fields })
  },

  buildResponse(): Record<string, unknown> | null {
    const response: Record<string, unknown> = {}
    for (const field of this.data.fields) {
      if (field.required && !field.value) {
        wx.showToast({ title: `${t('relays.validation.required')}：${field.label}`, icon: 'none' })
        return null
      }
      if (!field.value) continue
      if (field.field_type === 'number') {
        const num = Number(field.value)
        if (!Number.isFinite(num)) {
          wx.showToast({ title: `${field.label} ${t('relays.type.number')}`, icon: 'none' })
          return null
        }
        response[field.label] = num
      } else if (field.field_type === 'checkbox') {
        response[field.label] = field.value.split(',').filter(Boolean)
      } else {
        response[field.label] = field.value
      }
    }
    return response
  },

  async onSubmit() {
    if (!this.data.relay || this.data.relay.my_response || this.data.relay.status !== 'open') return
    const response = this.buildResponse()
    if (!response) return
    this.setData({ submitting: true })
    try {
      await submitRelayResponse(this.data.relay.id, response)
      wx.showToast({ title: t('relays.submit_success'), icon: 'success' })
      this.load(this.data.relay.id)
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('common.fail'), icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },
})

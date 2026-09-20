import { adminRelayResponses, getRelay } from '../../services/relays'
import type { RelayDetail, RelayResponseRow } from '../../types/api'
import { locale } from '../../utils/i18n'

type RowView = RelayResponseRow & { pairs: Array<{ label: string; value: string }> }

function toText(value: unknown): string {
  if (Array.isArray(value)) return value.join('、')
  if (value === null || value === undefined) return ''
  return String(value)
}

Page({
  data: {
    lang: locale.get(),
    loading: true,
    relay: null as RelayDetail | null,
    rows: [] as RowView[],
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
    this.setData({ loading: true, lang: locale.get() })
    try {
      const [relay, page] = await Promise.all([getRelay(id), adminRelayResponses(id)])
      this.setData({
        relay,
        rows: page.items.map((row) => ({
          ...row,
          pairs: relay.fields.map((field) => ({ label: field.label, value: toText(row.response[field.label]) })),
        })),
      })
    } finally {
      this.setData({ loading: false })
    }
  },
})

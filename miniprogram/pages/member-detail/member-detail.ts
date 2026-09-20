import { getMember } from '../../services/directory'
import type { MemberDetail } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type MemberCard = MemberDetail & {
  initial: string
  contactRows: Array<{ label: string; value: string }>
  companyRows: Array<{ label: string; value: string }>
  storyRows: Array<{ label: string; value: string }>
  chamberRows: Array<{ label: string; value: string }>
}

function valueOrEmpty(value: unknown): string {
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

function row(label: string, value: unknown): { label: string; value: string } | null {
  const text = valueOrEmpty(value)
  return text ? { label, value: text } : null
}

function rows(items: Array<{ label: string; value: unknown }>): Array<{ label: string; value: string }> {
  return items
    .map((item) => row(item.label, item.value))
    .filter((item): item is { label: string; value: string } => Boolean(item))
}

function toCard(member: MemberDetail): MemberCard {
  return {
    ...member,
    initial: member.name ? member.name.charAt(0) : '·',
    contactRows: rows([
      { label: t('member.mobile'), value: member.phone },
      { label: t('member.wechat'), value: member.wechat_id },
      { label: t('member.mailbox'), value: member.email },
    ]),
    companyRows: rows([
      { label: t('member.company_name'), value: member.company_name },
      { label: t('member.position'), value: member.position },
      { label: t('member.location'), value: member.company_address },
      { label: t('member.founded_at'), value: member.company_founded_at },
      { label: t('member.profession'), value: member.profession },
      { label: t('member.profession_en'), value: member.profession_en },
    ]),
    storyRows: rows([
      { label: t('member.bio'), value: member.bio },
      { label: t('member.business_desc'), value: member.business_description },
      { label: t('member.referrals_needed'), value: member.referrals_needed },
      { label: t('member.experience'), value: member.personal_experience },
      { label: t('member.resources'), value: member.resources_offered },
    ]),
    chamberRows: rows([
      { label: t('member.chapter'), value: member.chamber_chapter },
      { label: t('member.member_no'), value: member.chamber_member_no },
      { label: t('member.join_date'), value: member.chamber_join_date },
      { label: t('member.score'), value: member.chamber_score },
    ]),
  }
}

Page({
  data: {
    lang: locale.get(),
    loading: true,
    member: null as MemberCard | null,
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
      const member = await getMember(id)
      this.setData({ lang: locale.get(), member: toCard(member) })
      wx.setNavigationBarTitle({ title: member.name || t('member.card_title') })
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('member.load_failed'), icon: 'none' })
      this.setData({ member: null })
    } finally {
      this.setData({ loading: false })
    }
  },

  copyText(e: WechatMiniprogram.BaseEvent) {
    const value = String(e.currentTarget.dataset.value || '')
    if (!value) return
    wx.setClipboardData({ data: value })
  },
})

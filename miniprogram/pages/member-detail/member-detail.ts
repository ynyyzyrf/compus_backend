import { getMember } from '../../services/directory'
import type { MemberDetail } from '../../types/api'
import { locale, t } from '../../utils/i18n'
import { requestAlumniContact } from '../../utils/connection-actions'
import { connectionSummary } from '../../services/connections'
import { session } from '../../utils/session'

type MemberCard = MemberDetail & {
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
    canAdd: false,
    canMessage: false,
    memberId: 0,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (!Number.isFinite(id)) {
      this.setData({ loading: false })
      return
    }
    this.setData({ memberId: id })
  },

  onShow() { if (this.data.memberId) this.load(this.data.memberId) },

  async load(id: number) {
    this.setData({ loading: true, canAdd: false, canMessage: false })
    try {
      const member = await getMember(id)
      const isOwnCard = member.id === session.getUser()?.id
      this.setData({ lang: locale.get(), member: toCard(member), canMessage: !isOwnCard && Boolean(member.is_friend) })
      wx.setNavigationBarTitle({ title: member.name || t('member.card_title') })
      const summary = !isOwnCard && !member.is_friend ? await connectionSummary().catch(() => null) : null
      this.setData({ canAdd: Boolean(summary?.eligible) })
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
  onAvatarError(e: WechatMiniprogram.BaseEvent) {
    const { id, src } = e.currentTarget.dataset
    if (src && this.data.member?.id === Number(id) && this.data.member.avatar_url === src) {
      this.setData({ 'member.avatar_url': null })
    }
  },
  addFriend() {
    const member = this.data.member
    if (member && this.data.canAdd) requestAlumniContact(member.id, member.name)
  },
  openMessages() {
    if (this.data.canMessage && this.data.member) {
      wx.navigateTo({ url: `/pages/friend-messages/friend-messages?id=${this.data.member.id}` })
    }
  },
})

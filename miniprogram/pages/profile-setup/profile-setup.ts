import { getMyProfile, updateMyProfile } from '../../services/profile'
import { locale } from '../../utils/i18n'
import { session } from '../../utils/session'
import type { MyProfile, MyProfileUpdate } from '../../types/api'

// 表單字段（user_name 不可編輯，置頂只讀顯示）
type FormKey =
  | 'name_en'
  | 'phone'
  | 'wechat_id'
  | 'email'
  | 'company_name'
  | 'company_address'
  | 'company_founded_at'
  | 'profession'
  | 'profession_en'
  | 'position'
  | 'business_description'
  | 'referrals_needed'
  | 'personal_experience'
  | 'resources_offered'
  | 'chamber_chapter'
  | 'chamber_member_no'
  | 'chamber_join_date'
  | 'chamber_score'
  | 'bio'

Page({
  data: {
    lang: locale.get(),
    profile: null as MyProfile | null,
    saving: false,
  },

  onLoad() {
    this.setData({ lang: locale.get() })
    this.load()
  },

  async load() {
    try {
      const profile = await getMyProfile()
      this.setData({ profile })
    } catch (e) {
      console.error('load profile failed', e)
    }
  },

  onField(e: WechatMiniprogram.CustomEvent<{ value: string }>, key: FormKey) {
    const { value } = e.detail
    this.setData({ [`profile.${key}`]: value })
  },

  onNameEn(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'name_en') },
  onPhone(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'phone') },
  onWechatId(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'wechat_id') },
  onEmail(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'email') },
  onCompany(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'company_name') },
  onCompanyAddr(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'company_address') },
  onCompanyDate(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'company_founded_at') },
  onProfession(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'profession') },
  onProfessionEn(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'profession_en') },
  onPosition(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'position') },
  onBusiness(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'business_description') },
  onReferrals(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'referrals_needed') },
  onExperience(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'personal_experience') },
  onResources(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'resources_offered') },
  onChamber(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'chamber_chapter') },
  onChamberNo(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'chamber_member_no') },
  onChamberJoin(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'chamber_join_date') },
  onChamberScore(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    const v = e.detail.value
    const num = v ? Number(v) : null
    if (num !== null && Number.isNaN(num)) return
    this.setData({ 'profile.chamber_score': num })
  },
  onBio(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'bio') },

  _buildPayload(): MyProfileUpdate {
    const p = this.data.profile
    if (!p) return {}
    const cleanStr = (v: string | null) => (v && v.trim() ? v.trim() : null)
    const score = p.chamber_score == null ? undefined : Number(p.chamber_score)
    return {
      name_en: cleanStr(p.name_en),
      phone: cleanStr(p.phone),
      wechat_id: cleanStr(p.wechat_id),
      email: cleanStr(p.email),
      company_name: cleanStr(p.company_name),
      company_address: cleanStr(p.company_address),
      company_founded_at: cleanStr(p.company_founded_at),
      profession: cleanStr(p.profession),
      profession_en: cleanStr(p.profession_en),
      position: cleanStr(p.position),
      business_description: cleanStr(p.business_description),
      referrals_needed: cleanStr(p.referrals_needed),
      personal_experience: cleanStr(p.personal_experience),
      resources_offered: cleanStr(p.resources_offered),
      chamber_chapter: cleanStr(p.chamber_chapter),
      chamber_member_no: cleanStr(p.chamber_member_no),
      chamber_join_date: cleanStr(p.chamber_join_date),
      chamber_score: score,
      bio: cleanStr(p.bio),
    }
  },

  async onSave() {
    const profile = await this._persist()
    if (!profile) return
    session.setUser(profile)
    session.markOnboarded()
    wx.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => wx.navigateBack({ delta: 1 }), 600)
  },

  async onSkip() {
    // 即使跳過也算 onboarding 完成，不再打擾
    session.markOnboarded()
    wx.navigateBack({ delta: 1 })
  },

  async _persist(): Promise<MyProfile | null> {
    if (this.data.saving) return null
    this.setData({ saving: true })
    try {
      return await updateMyProfile(this._buildPayload())
    } catch (e) {
      wx.showToast({ title: (e as Error).message || '保存失敗', icon: 'none' })
      return null
    } finally {
      this.setData({ saving: false })
    }
  },
})

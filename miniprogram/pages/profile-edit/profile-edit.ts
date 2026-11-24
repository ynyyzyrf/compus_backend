import { getMyProfile, updateMyProfile } from '../../services/profile'
import { locale } from '../../utils/i18n'
import { session } from '../../utils/session'
import type { MyProfile, MyProfileUpdate } from '../../types/api'

const DEFAULT_PROFILE_NAME = '未命名校友'

type FormKey =
  | 'name' | 'name_en' | 'phone' | 'wechat_id' | 'email' | 'city'
  | 'company_name' | 'company_address' | 'company_founded_at'
  | 'profession' | 'profession_en' | 'position'
  | 'business_description' | 'referrals_needed'
  | 'personal_experience' | 'resources_offered'
  | 'bio'

function leaveProfilePage() {
  if (getCurrentPages().length > 1) {
    wx.navigateBack({ delta: 1 })
    return
  }
  wx.switchTab({ url: '/pages/mine/mine' })
}

Page({
  data: {
    lang: locale.get(),
    profile: null as MyProfile | null,
    nameEnDraft: '',
    nameEnSelectionEnd: -1,
    saving: false,
  },

  onLoad() {
    this.setData({ lang: locale.get() })
    this.load()
  },

  async load() {
    try {
      const profile = await getMyProfile()
      this.setData({
        nameEnDraft: profile.name_en || profile.name_en_display || '',
        nameEnSelectionEnd: -1,
        profile: {
          ...profile,
          name: profile.name === DEFAULT_PROFILE_NAME ? '' : profile.name,
        },
      })
    } catch (e) {
      console.error('load profile failed', e)
    }
  },

  onField(e: WechatMiniprogram.CustomEvent<{ value: string }>, key: FormKey) {
    this.setData({ [`profile.${key}`]: e.detail.value })
  },

  onName(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'name') },
  onNameEn(e: WechatMiniprogram.Input) {
    this.setData({ nameEnDraft: e.detail.value, nameEnSelectionEnd: -1 })
    this.onField(e, 'name_en')
  },
  onNameEnFocus() { this.setData({ nameEnSelectionEnd: this.data.nameEnDraft.length }) },
  onNameEnBlur() { this.setData({ nameEnSelectionEnd: -1 }) },
  onPhone(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'phone') },
  onWechatId(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'wechat_id') },
  onEmail(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'email') },
  onCity(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'city') },
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
  onBio(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.onField(e, 'bio') },

  _buildPayload(): MyProfileUpdate {
    const p = this.data.profile
    if (!p) return {}
    const cleanStr = (v: string | null) => (v && v.trim() ? v.trim() : null)
    const name = p.name.trim() || p.name_en?.trim() || DEFAULT_PROFILE_NAME
    return {
      name,
      name_en: cleanStr(p.name_en),
      phone: cleanStr(p.phone),
      wechat_id: cleanStr(p.wechat_id),
      email: cleanStr(p.email),
      city: cleanStr(p.city),
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
      bio: cleanStr(p.bio),
    }
  },

  async onSave() {
    if (this.data.saving) return
    if (!this.data.profile?.name.trim() && !this.data.profile?.name_en?.trim()) {
      wx.showToast({ title: '请填写姓名', icon: 'none' })
      return
    }
    const payload = this._buildPayload()
    this.setData({ saving: true })
    try {
      const profile = await updateMyProfile(payload)
      if (profile.name !== payload.name) throw new Error('姓名未保存，请稍后重试')
      session.setUser(profile)
      session.markOnboarded()
      wx.showToast({ title: '已保存', icon: 'success' })
      leaveProfilePage()
    } catch (e) {
      wx.showToast({ title: (e as Error).message || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})

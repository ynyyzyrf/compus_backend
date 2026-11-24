const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const ts = require('typescript')

const root = path.resolve(__dirname, '..')
function load(file, modules = {}, globals = {}) {
  const source = fs.readFileSync(path.join(root, file), 'utf8')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  })
  const exports = {}
  vm.runInNewContext(outputText, { exports, require: name => modules[name], ...globals }, { filename: file })
  return exports
}

function loadPage(name, modules, wx, globals = {}) {
  let page
  load(`miniprogram/pages/${name}/${name}.ts`, modules, {
    Page: definition => { page = {
      ...definition,
      data: { ...definition.data },
      setData(patch, done) { Object.assign(this.data, patch); done?.() },
    } },
    wx,
    ...globals,
  })
  return page
}

const academics = load('miniprogram/utils/academic.ts')
const nodes = [
  { id: 1, name: '大学', type: 'school', parent_id: null },
  { id: 2, name: '工程学院', type: 'college', parent_id: 1 },
  { id: 3, name: '计算机系', type: 'department', parent_id: 2 },
  { id: 4, name: '软件工程', type: 'major', parent_id: 3 },
  { id: 5, name: '2班', type: 'class', parent_id: 4, entry_year: 2018 },
  { id: 6, name: '12班', type: 'class', parent_id: 4, entry_year: 2018 },
  { id: 7, name: '2017級1班', type: 'class', parent_id: 3 },
]

test('home shows activity previews and keeps pinned announcements separate without requesting relays', async () => {
  const navigation = []
  let relayRequests = 0
  const now = Date.now()
  const date = hours => new Date(now + hours * 3600000).toISOString()
  const activities = [
    { id: 1, status: 'finished', start_at: date(-20) },
    { id: 2, status: 'signing', start_at: date(24), signup_start_at: date(12), capacity: 20, signup_count: 0, cover_url: null },
    { id: 3, status: 'signing', start_at: date(16), signup_start_at: date(-10), capacity: 20, signup_count: 20 },
    { id: 4, status: 'upcoming', start_at: date(8), cover_url: 'https://example.com/activity-4.jpg' },
  ]
  const page = loadPage('home', {
    '../../services/activities': { listActivities: async () => activities },
    '../../services/articles': { listArticles: async () => [{ id: 1, is_pinned: true }, { id: 2 }] },
    '../../services/relays': { listRelays: async () => { relayRequests += 1; return [] } },
    '../../utils/session': { session: { getToken: () => 'test-session' } },
    '../../utils/i18n': { t: key => key },
  }, { navigateTo: options => navigation.push(options.url) })
  await page.fetchHomeContent()

  assert.equal(page.data.pinnedArticle.id, 1)
  assert.deepEqual(Array.from(page.data.latestArticles, item => item.id), [2])
  assert.deepEqual(Array.from(page.data.latestActivities, item => item.statusText), ['报名已截止', '名额已满', '报名未开始'])
  assert.deepEqual(Array.from(page.data.latestActivities, item => item.canSignUp), [false, false, false])
  assert.equal(page.data.latestActivities[0].previewUrl, 'https://example.com/activity-4.jpg')
  assert.equal(page.data.latestActivities[2].previewUrl, '/assets/campus-hero.jpg')
  page.onActivityPreviewError({ currentTarget: { dataset: { id: 4, src: 'https://example.com/activity-4.jpg' } } })
  assert.equal(page.data['latestActivities[0].previewUrl'], '/assets/campus-hero.jpg')
  assert.equal(relayRequests, 0)
  assert.equal(page.data.contentFailed, false)
  page.goActivityDetail({ currentTarget: { dataset: { id: 4 } } })
  assert.deepEqual(navigation, ['/pages/activity-detail/activity-detail?id=4'])
})

test('mine shows its relay dot only for active relays and skips relay requests for guests', async () => {
  const requests = []
  const user = { id: 1, name: '张明', role: 'super_admin' }
  const expired = { deadline: new Date(Date.now() - 3600000).toISOString() }
  let pages = [[expired]]
  let isGuest = false
  const relays = load('miniprogram/services/relays.ts', {
    './request': { request: async ({ url, silent }) => {
      const params = new URLSearchParams(url.split('?')[1])
      assert.equal(params.get('status'), 'open')
      assert.equal(silent, true)
      const page = Number(params.get('page'))
      requests.push(page)
      return pages[page - 1] ?? []
    } },
  })
  const mine = loadPage('mine', {
    '../../config/env': { IS_DEV: false },
    '../../services/auth': { ensureLogin: async () => user },
    '../../services/profile': { getMyProfile: async () => user },
    '../../services/connections': { connectionSummary: async () => null },
    '../../services/relays': relays,
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: key => key },
    '../../utils/session': { session: { isGuest: () => isGuest, getToken: () => isGuest ? '' : 'token', setUser() {} } },
  }, { setNavigationBarTitle() {} })

  await mine.refresh()
  assert.equal(mine.data.showRelayDot, false)

  pages = [Array(100).fill(expired), [{ deadline: null }]]
  await mine.refresh()
  assert.equal(mine.data.showRelayDot, true)

  isGuest = true
  await mine.refresh()
  assert.equal(mine.data.showRelayDot, false)
  assert.deepEqual(requests, [1, 1, 2])
})

test('home shortcut opens alumni search only for eligible directory users', async () => {
  const app = { globalData: {} }
  const globals = { getApp: () => app }
  const tabs = []
  let classId = null
  const home = loadPage('home', {}, { switchTab: options => tabs.push(options.url) }, globals)
  const directory = loadPage('directory', {
    '../../services/auth': { ensureLogin: async () => ({ id: 1 }) },
    '../../services/affiliation': { getMyAffiliation: async () => ({ class_id: classId }), getAffiliationOptions: async () => nodes },
    '../../services/directory': { getDirectoryTree: async () => ({ nodes, scope_level: 'class' }), searchMembers: async () => ({ items: [], total: 0 }) },
    '../../utils/academic': academics,
    '../../utils/session': { session: { isGuest: () => false } },
  }, {}, globals)

  home.goFindAlumni()
  await directory.init()
  assert.equal(directory.data.discover, false)
  assert.equal(directory.data.relation, '')
  assert.equal(app.globalData.openDirectoryDiscovery, undefined)

  classId = 5
  home.goFindAlumni()
  await directory.init()
  assert.equal(directory.data.discover, true)
  assert.equal(directory.data.relation, 'class')
  assert.equal(app.globalData.openDirectoryDiscovery, undefined)
  assert.deepEqual(tabs, ['/pages/directory/directory', '/pages/directory/directory'])
})

test('relation filters explain missing class affiliation without requesting unrelated members', () => {
  const notices = []
  let searches = 0
  const page = loadPage('directory', {
    '../../services/directory': { searchMembers: () => { searches += 1 } },
  }, { showToast: options => notices.push(options.title) })
  page.changeRelation({ currentTarget: { dataset: { id: 'class' } } })
  assert.deepEqual(notices, ['请先确认所属班级后使用筛选'])
  assert.equal(searches, 0)
})

test('finding a class handles legacy paths and submits the exact matching class', async () => {
  const sent = []
  const page = loadPage('org-select', {
    '../../services/auth': { ensureLogin: async () => ({ id: 9, name: '未命名校友' }) },
    '../../services/affiliation': {
      getMyAffiliation: async () => ({}),
      getAffiliationOptions: async () => nodes,
      submitAffiliation: async (id, name) => {
        sent.push([id, name])
        return { pending_org_path: '软件工程 · 2018级 2班' }
      },
    },
    '../../utils/session': { session: { isGuest: () => false, getUser: () => null } },
    '../../utils/academic': academics,
  }, { pageScrollTo() {}, showToast() {} })
  await page.load()
  assert.equal(page.data.classes.length, 3)
  page.search({ detail: { value: '2018 软件工程 2 班' } })
  assert.equal(page.data.shown.length, 1)
  assert.equal(page.data.shown[0].id, 5)
  page.choose({ currentTarget: { dataset: { id: 5 } } })
  page.onNameInput({ detail: { value: ' 张明 ' } })
  await page.submit()
  assert.deepEqual(sent, [[5, '张明']])
  assert.match(page.data.pendingPath, /软件工程/)
})

test('keyword and academic filters are sent together; a discovery card does not open a full profile', async () => {
  const queries = []
  const friendRequests = []
  const navigation = []
  const page = loadPage('directory', {
    '../../services/auth': { ensureLogin: async () => ({ id: 1 }) },
    '../../services/affiliation': {},
    '../../services/directory': {
      searchMembers: async (...args) => {
        queries.push(args)
        return { items: [{ id: 8, name: '张明', can_view_profile: false }], total: 1 }
      },
    },
    '../../utils/academic': academics,
    '../../utils/connection-actions': { requestAlumniContact: (...args) => friendRequests.push(args) },
    '../../utils/session': {},
  }, { navigateTo: opts => navigation.push(opts.url) })
  page.setData({ userId: 1, eligible: true, discover: true, keyword: '张明' })
  page.onFilter({ detail: { entry_year: 2018, major_id: 4 } })
  await new Promise(resolve => setImmediate(resolve))
  assert.deepEqual(queries[0], ['张明', 1, 20, { entry_year: 2018, major_id: 4 }, true, 'all', 'class'])
  page.changeRelation({ currentTarget: { dataset: { id: 'year' } } })
  await new Promise(resolve => setImmediate(resolve))
  assert.deepEqual(queries[1], ['张明', 1, 20, { entry_year: 2018, major_id: 4 }, true, 'all', 'year'])
  page.changeRelation({ currentTarget: { dataset: { id: 'year' } } })
  assert.equal(page.data.relation, 'year')
  assert.equal(queries.length, 2)
  page.onMemberTap({ currentTarget: { dataset: { id: 8 } } })
  assert.deepEqual(friendRequests, [[8, '张明']])
  assert.deepEqual(navigation, [])
})

test('personal profile selects the complete default English name without saving generated pinyin as a custom name', async () => {
  const page = loadPage('profile-edit', {
    '../../services/profile': { getMyProfile: async () => ({ name: '黄康婷', name_en: null, name_en_display: 'KANGTING HUANG' }) },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' } },
  }, {})
  await page.load()
  assert.equal(page.data.nameEnDraft, 'KANGTING HUANG')
  assert.equal(page._buildPayload().name_en, null)
  page.onNameEnFocus()
  assert.equal(page.data.nameEnSelectionEnd, 'KANGTING HUANG'.length)
  page.onNameEn({ detail: { value: 'KATIE HUANG' } })
  assert.equal(page.data['profile.name_en'], 'KATIE HUANG')
  assert.equal(page.data.nameEnSelectionEnd, -1)
  page.onNameEnBlur()
  page.onNameEnFocus()
  assert.equal(page.data.nameEnSelectionEnd, 'KATIE HUANG'.length)
  page.onNameEn({ detail: { value: '' } })
  page.data.profile.name_en = page.data['profile.name_en']
  assert.equal(page._buildPayload().name_en, null)
})

test('mine personal card opens the profile editor', () => {
  const navigation = []
  const mine = loadPage('mine', {
    '../../config/env': { IS_DEV: false },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' } },
  }, { navigateTo: ({ url }) => navigation.push(url) })
  mine.goProfileCard()
  assert.deepEqual(navigation, ['/pages/profile-edit/profile-edit'])
})

test('retries a friend message with the same client id and clears the draft after success', async () => {
  const calls = []
  const page = loadPage('friend-messages', {
    '../../services/connections': { sendFriendMessage: async (peer, message, id) => {
      calls.push({ peer, message, id })
      if (calls.length === 1) throw new Error('connection interrupted')
      return { id: 1, message, sender_id: 3, created_at: '2026-11-24T08:00:00Z' }
    } },
    '../../utils/session': { session: { getUser: () => ({ id: 3 }) } },
  }, { showToast() {} })
  page.setData({ ready: true, peerId: 8, draft: '周末见' })
  await page.send()
  assert.equal(page.data.draft, '周末见')
  await page.send()
  assert.deepEqual(calls[0], calls[1])
  assert.equal(page.data.draft, '')
  assert.equal(page.data.messages.length, 1)
})

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const ts = require('typescript')
const root = path.resolve(__dirname, '..')

function load(file, modules, globals) {
  const exports = {}
  const output = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  vm.runInNewContext(output, { exports, require: name => modules[name], ...globals })
  return exports
}
function page(name, modules, wx, globals = {}) {
  let result
  load(`miniprogram/pages/${name}/${name}.ts`, modules, { wx, ...globals, Page: definition => {
    result = { ...definition, data: { ...definition.data }, setData(patch) { Object.assign(this.data, patch) } }
  } })
  return result
}
const original = { id: 2, name: '张明', basic_visibility: 'classmates', contact_visibility: 'private', details_visibility: 'private' }
function settings(profileService = {}, connections = {}, wx = {}) {
  return page('settings', {
    '../../services/auth': { ensureLogin: async () => ({ id: 2 }) },
    '../../services/profile': { getMyProfile: async () => ({ ...original }), ...profileService },
    '../../services/connections': { connectionSummary: async () => ({ eligible: true, discoverable: true }), ...connections },
    '../../utils/session': { session: { getToken: () => 'session-a', isGuest: () => false, setUser() {} } },
  }, { showToast() {}, showModal() {}, ...wx })
}

test('settings saves only the chosen visibility field and serializes privacy updates', async () => {
  const writes = []
  let finish
  const screen = settings({ updateMyProfile: async payload => {
    writes.push({ ...payload })
    await new Promise(resolve => { finish = resolve })
    return { ...original, ...payload }
  } })
  await screen.load()
  const first = screen.onVisibility({ detail: { key: 'contact_visibility', value: 'friends' } })
  await screen.onVisibility({ detail: { key: 'details_visibility', value: 'classmates' } })
  assert.deepEqual(writes, [{ contact_visibility: 'friends' }])
  assert.equal(screen.data.profile.contact_visibility, 'private')
  finish()
  await first
  assert.equal(screen.data.profile.contact_visibility, 'friends')
  assert.equal(screen.data.profile.details_visibility, 'private')
  assert.equal(screen.data.saving, false)
})

test('failed privacy save keeps the confirmed permissions; private basic details disable discovery', async () => {
  const errors = []
  let fail = true
  const screen = settings({ updateMyProfile: async payload => {
    if (fail) throw Error('保存失败')
    return { ...original, ...payload }
  } }, {}, { showModal: value => errors.push(value.content) })
  await screen.load()
  await screen.onVisibility({ detail: { key: 'basic_visibility', value: 'private' } })
  assert.equal(screen.data.profile.basic_visibility, 'classmates')
  assert.equal(screen.data.discoverable, true)
  assert.equal(screen.data.saving, false)
  assert.deepEqual(errors, ['保存失败'])
  fail = false
  await screen.onVisibility({ detail: { key: 'basic_visibility', value: 'private' } })
  assert.equal(screen.data.profile.basic_visibility, 'private')
  assert.equal(screen.data.discoverable, false)
})

test('discovery requires an approved class and saves only after confirmation', async () => {
  const writes = []
  let modal
  const screen = settings({}, { updateDiscoverability: async value => {
    writes.push(value)
    return { discoverable: value }
  } }, { showModal: value => { modal = value } })
  await screen.load()
  screen.setData({ eligible: false, discoverable: false })
  screen.setDiscoverability()
  assert.deepEqual(writes, [])
  assert.equal(modal, undefined)
  screen.setData({ eligible: true })
  screen.setDiscoverability()
  await modal.success({ confirm: false })
  assert.deepEqual(writes, [])
  screen.setDiscoverability()
  await modal.success({ confirm: true })
  assert.deepEqual(writes, [true])
  assert.equal(screen.data.discoverable, true)
})

test('cached login routes an unassigned user to class selection and leaves approved or pending users alone', async () => {
  for (const [affiliation, shouldRedirect] of [[{}, true], [{ class_id: 4 }, false], [{ pending_class_id: 4 }, false]]) {
    const navigation = []
    const service = load('miniprogram/services/startup.ts', {
      './affiliation': { getMyAffiliation: async () => affiliation },
      '../utils/session': { session: { getToken: () => 'cached-session', getUser: () => ({ id: 8 }), isGuest: () => false } },
    }, { getCurrentPages: () => [{ route: 'pages/mine/mine' }], wx: { reLaunch: value => navigation.push(value.url) } })
    const result = await service.routeUnassignedUser()
    assert.equal(result, shouldRedirect)
    assert.deepEqual(navigation, shouldRedirect ? ['/pages/org-select/org-select'] : [])
  }
})

test('startup ignores stale affiliation responses after switching accounts', async () => {
  let token = 'first-user'
  let finish
  const navigation = []
  const service = load('miniprogram/services/startup.ts', {
    './affiliation': { getMyAffiliation: () => new Promise(resolve => { finish = resolve }) },
    '../utils/session': { session: { getToken: () => token, getUser: () => ({ id: 8 }), isGuest: () => false } },
  }, { getCurrentPages: () => [{ route: 'pages/mine/mine' }], wx: { reLaunch: value => navigation.push(value.url) } })
  const pending = service.routeUnassignedUser()
  token = 'second-user'
  finish({})
  assert.equal(await pending, false)
  assert.deepEqual(navigation, [])
})

test('an unassigned user can return home and browse without being sent back to class selection', async () => {
  const navigation = []
  let fetched = false
  const screen = page('home', {
    '../../services/auth': { ensureLogin: async () => ({ id: 8, role: 'user' }) },
    '../../services/affiliation': { getMyAffiliation: async () => ({ class_id: null, pending_class_id: null }) },
    '../../utils/session': { session: { isGuest: () => false } },
  }, { reLaunch: value => navigation.push(value.url) }, { getApp: () => ({ globalData: { pendingOnboarding: true } }) })
  screen.fetchHomeContent = async () => { fetched = true }
  await screen.onShow()
  assert.deepEqual(navigation, [])
  assert.equal(fetched, true)
})

test('class reviewers do not request super-admin-only missing-class feedback', async () => {
  let missingCalls = 0
  const screen = page('admin-affiliations', {
    '../../services/auth': { ensureLogin: async () => ({ id: 2, role: 'class_admin' }) },
    '../../services/admin': {
      listAffiliationRequests: async () => [{ user_id: 8, class_id: 4 }],
      listMissingClasses: () => { missingCalls++; throw Error('forbidden') },
    },
  }, {})
  await screen.load()
  assert.equal(screen.data.items.length, 1)
  assert.equal(screen.data.error, '')
  assert.equal(missingCalls, 0)
})

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const ts = require('typescript')

const root = path.resolve(__dirname, '..')

function loadPage(file, modules, wx) {
  modules['../../services/request'] ??= { ApiError: class ApiError extends Error {} }
  let definition
  const source = fs.readFileSync(path.join(root, file), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  vm.runInNewContext(compiled, {
    exports: {},
    require: (name) => modules[name],
    Page: (value) => { definition = value },
    wx,
    getApp: () => ({ globalData: {} }),
    getCurrentPages: () => [{}, {}],
    console,
  }, { filename: file })
  assert.ok(definition, `${file} must register a page`)
  return {
    ...definition,
    data: { ...definition.data },
    setData(update) {
      for (const [key, value] of Object.entries(update)) {
        const parts = key.split('.')
        let target = this.data
        for (const part of parts.slice(0, -1)) target = target[part]
        target[parts.at(-1)] = value
      }
    },
  }
}

test('login shows request failures after the loading overlay closes', async () => {
  const events = []
  const page = loadPage('miniprogram/pages/login/login.ts', {
    '../../config/env': { IS_DEV: false },
    '../../services/auth': {
      loginWithWechat: async () => { throw new Error('request:fail url not in domain list') },
    },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: (key) => key },
    '../../utils/session': { session: { hasOnboarded: () => false } },
  }, {
    showLoading: () => events.push('showLoading'),
    hideLoading: () => events.push('hideLoading'),
    showModal: (options) => events.push(`showModal:${options.content}`),
    switchTab: () => events.push('switchTab'),
  })
  await page.onLogin()
  assert.deepEqual(events, [
    'showLoading',
    'hideLoading',
    'showModal:request:fail url not in domain list',
  ])
  assert.equal(page.data.loading, false)
  assert.equal('phoneSheetOpen' in page.data, false)
})

test('login reports a failed home navigation', async () => {
  const events = []
  const page = loadPage('miniprogram/pages/login/login.ts', {
    '../../config/env': { IS_DEV: false },
    '../../services/auth': { loginWithWechat: async () => ({ id: 1 }) },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: (key) => key },
    '../../utils/session': { session: {
      hasOnboarded: () => true,
      getUser: () => ({ id: 1, role: 'super_admin' }),
    } },
  }, {
    showLoading: () => events.push('showLoading'),
    hideLoading: () => events.push('hideLoading'),
    showModal: (options) => events.push(`showModal:${options.content}`),
    switchTab: (options) => {
      events.push(`switchTab:${options.url}`)
      options.fail({ errMsg: 'switchTab:fail test' })
    },
  })
  await page.confirmLogin()
  assert.deepEqual(events, [
    'showLoading',
    'hideLoading',
    'switchTab:/pages/home/home',
    'showModal:switchTab:fail test',
  ])
})

test('activity card navigates to its registered detail page', () => {
  const app = JSON.parse(fs.readFileSync(path.join(root, 'miniprogram/app.json'), 'utf8'))
  const route = 'pages/activity-detail/activity-detail'
  assert.ok(app.pages.includes(route))
  for (const extension of ['ts', 'wxml', 'json', 'wxss']) {
    assert.ok(fs.existsSync(path.join(root, `miniprogram/${route}.${extension}`)))
  }
  const listView = fs.readFileSync(path.join(root, 'miniprogram/pages/activities/activities.wxml'), 'utf8')
  assert.match(listView, /class="activity-card"[^>]*data-id="{{item\.id}}"[^>]*bindtap="onCardTap"/)

  const navigations = []
  const page = loadPage('miniprogram/pages/activities/activities.ts', {
    '../../services/activities': { listActivities: async () => [] },
    '../../services/auth': { ensureLogin: async () => ({}), goLogin() {} },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: (key) => key },
  }, {
    navigateTo: (options) => navigations.push(options.url),
    showToast() {},
  })
  page.onCardTap({ currentTarget: { dataset: { id: 37 } }, target: { dataset: {} } })
  assert.deepEqual(navigations, [`/${route}?id=37`])
})

for (const kind of ['profile-edit', 'profile-setup']) {
  test(`${kind} saves edited name and trusts server response`, async () => {
    const saved = []
    const navigations = []
    let serverName = '新姓名'
    const page = loadPage(`miniprogram/pages/${kind}/${kind}.ts`, {
      '../../services/profile': {
        getMyProfile: async () => ({}),
        updateMyProfile: async (payload) => {
          saved.push(payload)
          return { id: 1, name: serverName, role: 'user', status: 'active' }
        },
      },
      '../../utils/i18n': { locale: { get: () => 'zh-CN' } },
      '../../utils/session': { session: { setUser: (user) => saved.push(user), markOnboarded() {} } },
    }, {
      showToast() {},
      navigateBack: () => navigations.push('back'),
      switchTab: () => navigations.push('tab'),
    })
    page.data.profile = { name: '舊姓名', name_en: null, chamber_score: null }
    page.onName({ detail: { value: '新姓名' } })
    await page.onSave()
    assert.equal(saved[0].name, '新姓名')
    assert.equal(saved[1].name, '新姓名')
    assert.deepEqual(navigations, ['back'])

    serverName = '舊姓名'
    saved.length = 0
    navigations.length = 0
    await page.onSave()
    assert.equal(saved[0].name, '新姓名')
    assert.equal(saved.length, 1, 'stale server response must not update local user')
    assert.deepEqual(navigations, [])
  })
}

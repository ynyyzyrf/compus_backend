const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const ts = require('typescript')

const root = path.resolve(__dirname, '..')

function loadModule(file, modules, globals = {}) {
  const source = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const exports = {}
  vm.runInNewContext(source, {
    exports, require: (name) => modules[name], ...globals,
  }, { filename: file })
  return exports
}

test('wx.login code is the only login payload sent to the backend', async () => {
  const calls = []
  const session = {
    setToken: (token) => calls.push(`token:${token}`),
    setUser: (user) => calls.push(`user:${user.id}`),
  }
  const { loginWithWechat } = loadModule('miniprogram/services/auth.ts', {
    '../config/env': { IS_DEV: false },
    '../utils/session': { session },
    './request': {
      request: async (options) => {
        calls.push(JSON.stringify(options.data))
        return { access_token: 'token', user: { id: 7 } }
      },
      setUnauthorizedHandler: () => {},
    },
  }, {
    wx: { login: ({ success }) => success({ code: 'wx-one-use-code' }) },
  })
  await loginWithWechat()
  assert.deepEqual(calls, ['{"code":"wx-one-use-code"}', 'token:token', 'user:7'])
})

test('login page has no phone authorization and navigates after OpenID login', async () => {
  const pagePath = 'miniprogram/pages/login/login.ts'
  const events = []
  let page
  loadModule(pagePath, {
    '../../config/env': { IS_DEV: false },
    '../../services/auth': { loginWithWechat: async () => events.push('login') },
    '../../services/affiliation': { getMyAffiliation: async () => ({ class_id: 1 }) },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: (key) => key },
    '../../utils/session': { session: {
      getUser: () => ({ id: 7, role: 'super_admin' }), hasOnboarded: () => true,
    } },
  }, {
    Page: (definition) => { page = {
      ...definition, data: { ...definition.data },
      setData(update) { Object.assign(this.data, update) },
    } },
    getApp: () => ({ globalData: {} }),
    wx: {
      showLoading: () => events.push('showLoading'),
      hideLoading: () => events.push('hideLoading'),
      switchTab: (options) => events.push(`switchTab:${options.url}`),
    },
  })
  await page.onLogin()
  assert.deepEqual(events, [
    'showLoading', 'login', 'hideLoading', 'switchTab:/pages/home/home',
  ])
  assert.equal(page.data.loading, false)
  const view = fs.readFileSync(path.join(root, 'miniprogram/pages/login/login.wxml'), 'utf8')
  assert.doesNotMatch(view, /getPhoneNumber|bindgetphonenumber|phoneSheetOpen/)
})

test('login errors are shown after the loading overlay closes', async () => {
  const events = []
  let page
  loadModule('miniprogram/pages/login/login.ts', {
    '../../config/env': { IS_DEV: false },
    '../../services/auth': {
      loginWithWechat: async () => { throw new Error('request:fail url not in domain list') },
    },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: (key) => key },
    '../../utils/session': { session: { hasOnboarded: () => false } },
  }, {
    Page: (definition) => { page = {
      ...definition, data: { ...definition.data },
      setData(update) { Object.assign(this.data, update) },
    } },
    wx: {
      showLoading: () => events.push('showLoading'),
      hideLoading: () => events.push('hideLoading'),
      showModal: (options) => events.push(`showModal:${options.content}`),
    },
  })
  await page.onLogin()
  assert.deepEqual(events, [
    'showLoading', 'hideLoading',
    'showModal:request:fail url not in domain list',
  ])
})

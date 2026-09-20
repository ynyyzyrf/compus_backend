const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const ts = require('typescript')

const root = path.resolve(__dirname, '..')
const pagePath = path.join(root, 'miniprogram/pages/login/login.ts')

function loadLoginPage(loginWithWechat, events) {
  class ApiError extends Error {
    constructor(message, statusCode) {
      super(message)
      this.statusCode = statusCode
    }
  }
  const modules = {
    '../../config/env': { IS_DEV: false },
    '../../services/auth': { loginWithWechat },
    '../../services/request': { ApiError },
    '../../utils/i18n': { locale: { get: () => 'zh-CN' }, t: (key) => key },
    '../../utils/session': { session: {
      getToken: () => '', getUser: () => null, hasOnboarded: () => true,
    } },
  }
  let definition
  const source = ts.transpileModule(fs.readFileSync(pagePath, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  vm.runInNewContext(source, {
    exports: {},
    require: (name) => modules[name],
    Page: (value) => { definition = value },
    wx: {
      showLoading: () => events.push('showLoading'),
      hideLoading: () => events.push('hideLoading'),
      showModal: (options) => events.push(`showModal:${options.content}`),
      switchTab: (options) => events.push(`switchTab:${options.url}`),
    },
    getApp: () => ({ globalData: {} }),
  }, { filename: pagePath })
  const page = {
    ...definition,
    data: { ...definition.data },
    setData(update) { Object.assign(this.data, update) },
  }
  return { page, ApiError }
}

test('unbound account is asked for real WeChat phone authorization', async () => {
  const events = []
  const { page, ApiError } = loadLoginPage(
    async () => { throw new ApiError('phone required', 428) }, events,
  )
  await page.onLogin()
  assert.equal(page.data.phoneSheetOpen, true)
  assert.deepEqual(events, ['showLoading', 'hideLoading'])
  const view = fs.readFileSync(path.join(root, 'miniprogram/pages/login/login.wxml'), 'utf8')
  assert.match(view, /open-type="getPhoneNumber" bindgetphonenumber="onPhoneAuthorized"/)
  assert.match(view, /bindtap="openPhoneSheet"/)
  assert.doesNotMatch(view, /135\*\*\*\*5123|151\*\*\*\*5530/)
})

test('phone login can be tested before the backend requires it', () => {
  const { page } = loadLoginPage(async () => {}, [])
  page.openPhoneSheet()
  assert.equal(page.data.phoneSheetOpen, true)
})

test('phone authorization code is sent separately and login navigates home', async () => {
  const events = []
  const codes = []
  const { page } = loadLoginPage(async (code) => { codes.push(code) }, events)
  await page.onPhoneAuthorized({ detail: { code: 'phone-one-use-code' } })
  assert.deepEqual(codes, ['phone-one-use-code'])
  assert.deepEqual(events, [
    'showLoading', 'hideLoading', 'switchTab:/pages/home/home',
  ])
})

test('login error remains visible after loading overlay is gone', async () => {
  const events = []
  const { page, ApiError } = loadLoginPage(
    async () => { throw new ApiError('request:fail url not in domain list', 0) }, events,
  )
  await page.onLogin()
  assert.deepEqual(events, [
    'showLoading', 'hideLoading',
    'showModal:request:fail url not in domain list',
  ])
})

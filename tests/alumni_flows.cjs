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

function loadPage(name, modules, wx) {
  let page
  load(`miniprogram/pages/${name}/${name}.ts`, modules, {
    Page: definition => { page = {
      ...definition,
      data: { ...definition.data },
      setData(patch, done) { Object.assign(this.data, patch); done?.() },
    } },
    wx,
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
  assert.deepEqual(queries[0], ['张明', 1, 20, { entry_year: 2018, major_id: 4 }, true])
  page.onMemberTap({ currentTarget: { dataset: { id: 8 } } })
  assert.deepEqual(friendRequests, [[8, '张明']])
  assert.deepEqual(navigation, [])
})

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import { createRenderer, h, nextTick, reactive, ref } from 'vue'
import { createMemoryHistory, createRouter, RouterView, useRouter } from 'vue-router'

const { descriptor } = parse(
  readFileSync(new URL('../src/views/Login.vue', import.meta.url), 'utf8')
)
const loginScript = compileScript(descriptor, { id: 'login-navigation-test' }).content

function createNode(type, text = '') {
  return { type, text, children: [], parent: null }
}

const { createApp } = createRenderer({
  createElement: createNode,
  createText: (text) => createNode('text', text),
  createComment: (text) => createNode('comment', text),
  setText: (node, text) => {
    node.text = text
  },
  setElementText: (node, text) => {
    node.text = text
    node.children = []
  },
  parentNode: (node) => node.parent,
  nextSibling: (node) => node.parent?.children[node.parent.children.indexOf(node) + 1],
  patchProp: () => {},
  insert(node, parent, anchor = null) {
    if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1)
    const index = anchor ? parent.children.indexOf(anchor) : -1
    parent.children.splice(index < 0 ? parent.children.length : index, 0, node)
    node.parent = parent
  },
  remove(node) {
    if (!node.parent) return
    node.parent.children.splice(node.parent.children.indexOf(node), 1)
    node.parent = null
  }
})

function textContent(node) {
  return node.text + node.children.map(textContent).join('')
}

async function mountLogin({ separateRouter = false, valid = true, loginApi } = {}) {
  const messages = []
  let token = null
  let loginState
  let calls = 0

  const makeRouter = (loginComponent) => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/login', component: loginComponent },
        { path: '/manager/home', component: { render: () => h('main', '系统首页') } }
      ]
    })
    router.beforeEach((to) => (to.path === '/login' || token ? true : '/login'))
    return router
  }

  let importedRouter
  const bindings = {
    reactive,
    ref,
    useRouter,
    User: {},
    Lock: {},
    ElMessage: {
      success: (message) => messages.push(['success', message]),
      error: (message) => messages.push(['error', message])
    },
    get router() {
      return importedRouter
    },
    loginApi: async (form) => {
      calls++
      return loginApi ? loginApi(form) : { code: 200, data: { token: 'test-token' } }
    },
    useUser: () => ({
      saveLoginData: (data) => {
        token = data.token
      }
    })
  }

  const Login = {
    setup(props, context) {
      // Compile the real component script, replacing only its external dependencies.
      const body = loginScript
        .replace(/^import\s+.*?\s+from\s+['"].*?['"]\s*;?\r?$/gm, '')
        .replace('export default', 'return')
      const component = new Function(...Object.keys(bindings), body)(...Object.values(bindings))
      loginState = component.setup(props, context)
      loginState.formRef.value = { validate: async () => valid }
      return () => h('section', '登录页面')
    }
  }

  const activeRouter = makeRouter(Login)
  importedRouter = separateRouter ? makeRouter(Login) : activeRouter
  await activeRouter.push('/login')
  if (separateRouter) await importedRouter.push('/login')

  const root = createNode('root')
  const app = createApp({ render: () => h(RouterView) })
  app.use(activeRouter)
  app.mount(root)

  return {
    app,
    activeRouter,
    importedRouter,
    root,
    messages,
    get state() {
      return loginState
    },
    get token() {
      return token
    },
    get calls() {
      return calls
    }
  }
}

test('successful login replaces the login screen with the home screen', async (t) => {
  const view = await mountLogin()
  t.after(() => view.app.unmount())
  assert.equal(textContent(view.root), '登录页面')
  await view.state.login()
  await nextTick()
  assert.equal(view.activeRouter.currentRoute.value.path, '/manager/home')
  assert.equal(textContent(view.root), '系统首页')
  assert.equal(view.token, 'test-token')
  assert.equal(view.state.loadingValue.value, false)
  assert.deepEqual(view.messages, [['success', '登录成功']])
})

test('login updates the mounted app when an imported router is a different instance', async (t) => {
  const view = await mountLogin({ separateRouter: true })
  t.after(() => view.app.unmount())
  await view.state.login()
  await nextTick()
  assert.equal(view.activeRouter.currentRoute.value.path, '/manager/home')
  assert.equal(textContent(view.root), '系统首页')
  assert.equal(view.importedRouter.currentRoute.value.path, '/login')
})

test('invalid form stays on login without sending a request', async (t) => {
  const view = await mountLogin({ valid: false })
  t.after(() => view.app.unmount())
  await view.state.login()
  assert.equal(view.calls, 0)
  assert.equal(view.token, null)
  assert.equal(textContent(view.root), '登录页面')
  assert.equal(view.state.loadingValue.value, false)
})

test('rejected credentials stay on login and release the submit button', async (t) => {
  const view = await mountLogin({ loginApi: async () => ({ code: 400 }) })
  t.after(() => view.app.unmount())
  await view.state.login()
  assert.equal(view.calls, 1)
  assert.equal(view.token, null)
  assert.equal(textContent(view.root), '登录页面')
  assert.equal(view.state.loadingValue.value, false)
  assert.deepEqual(view.messages, [])
})

test('network failures allow retrying the login', async (t) => {
  const view = await mountLogin({
    loginApi: async () => {
      throw new Error('offline')
    }
  })
  t.after(() => view.app.unmount())
  await view.state.login()
  assert.equal(view.token, null)
  assert.equal(textContent(view.root), '登录页面')
  assert.equal(view.state.loadingValue.value, false)
})

test('repeated submissions send only one login request', async (t) => {
  let resolveLogin
  const response = new Promise((resolve) => {
    resolveLogin = resolve
  })
  const view = await mountLogin({ loginApi: () => response })
  t.after(() => view.app.unmount())
  const first = view.state.login()
  await view.state.login()
  await Promise.resolve()
  resolveLogin({ code: 200, data: { token: 'test-token' } })
  await first
  assert.equal(view.calls, 1)
  assert.equal(textContent(view.root), '系统首页')
  assert.equal(view.state.loadingValue.value, false)
})

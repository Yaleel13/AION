import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const dependency = createRequire(import.meta.url)
function dialog(responses) {
  const slots = []; let cursor = 0; let authenticated = 0; let closed = 0
  const calls = []
  const loadedModule = { exports: {} }
  const hooks = {
    useState(initial) {
      const index = cursor++
      if (!(index in slots)) slots[index] = initial
      return [slots[index], value => { slots[index] = value }]
    }, useEffect() {},
  }
  const code = ts.transpileModule(readFileSync('components/owner-auth-dialog.tsx', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  vm.runInNewContext(code, {
    module: loadedModule, exports: loadedModule.exports,
    require: name => name === 'react' ? hooks : dependency(name),
    fetch: async (...args) => { calls.push(args); return responses.shift() },
  })
  const render = () => { cursor = 0; return loadedModule.exports.OwnerAuthDialog({ open: true, onAuthenticated: () => authenticated++, onClose: () => closed++ }) }
  const flatten = node => Array.isArray(node) ? node.flatMap(flatten) : node?.props ? [node, ...flatten(node.props.children)] : [node]
  const element = type => flatten(render()).find(node => node?.type === type)
  return { calls, element, text: () => flatten(render()).filter(node => typeof node === 'string').join(''),
    counts: () => ({ authenticated, closed }) }
}

test('Boardroom opens only after the browser presents its newly created session', async () => {
  const h = dialog([Response.json({ authenticated: true }), Response.json({ authenticated: true })])
  h.element('input').props.onChange({ target: { value: 'test-owner' } })
  await h.element('form').props.onSubmit({ preventDefault() {} })
  assert.deepEqual(h.counts(), { authenticated: 1, closed: 1 })
  assert.equal(h.calls.length, 2)
  assert.equal(h.calls[1][1].cache, 'no-store')
  assert.equal(h.calls[1][1].credentials, 'same-origin')
  assert.equal(h.calls[1][1].body, undefined)
  assert.equal(h.element('input'), undefined) // Session-active view contains no token input.
})

test('a blocked session cookie leaves Boardroom locked with an actionable message', async () => {
  const h = dialog([Response.json({ authenticated: true }), Response.json({ authenticated: false })])
  h.element('input').props.onChange({ target: { value: 'test-owner' } })
  await h.element('form').props.onSubmit({ preventDefault() {} })
  assert.deepEqual(h.counts(), { authenticated: 0, closed: 0 })
  assert.match(h.text(), /did not retain the owner session/)
  assert.equal(h.element('input').props.value, '')
})

test('invalid credentials do not unlock Boardroom or start a session probe', async () => {
  const h = dialog([Response.json({ error: 'Invalid owner token.' }, { status: 403 })])
  h.element('input').props.onChange({ target: { value: 'wrong' } })
  await h.element('form').props.onSubmit({ preventDefault() {} })
  assert.deepEqual(h.counts(), { authenticated: 0, closed: 0 })
  assert.equal(h.calls.length, 1)
  assert.match(h.text(), /Invalid owner token/)
})

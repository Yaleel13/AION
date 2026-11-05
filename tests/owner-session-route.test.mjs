import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const require = createRequire(import.meta.url)

function harness() {
  const env = { AION_OWNER_TOKEN: "test-owner" }
  function load(path, dependencies = {}) {
    const loadedModule = { exports: {} }
    const code = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module: loadedModule,
      exports: loadedModule.exports,
      require: name => dependencies[name] ?? require(name),
      process: { env },
      Buffer,
      URL,
      Response,
    }, { filename: path })
    return loadedModule.exports
  }

  const headers = load("lib/aion/request-headers.ts")
  const session = load("lib/aion/owner-session.ts", { "./request-headers": headers })
  const route = load("app/api/aion/owner-session/route.ts", {
    "@/lib/aion/owner-session": session,
  })
  const login = async (url, token = "test-owner") => route.POST(new Request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  }))
  return { route, login }
}

test("loopback HTTP login emits a usable strict owner session cookie", async () => {
  const { route, login } = harness()
  const response = await login("http://127.0.0.1:3001/api/aion/owner-session")
  const cookie = response.headers.get("set-cookie")

  assert.equal(response.status, 200)
  assert.match(cookie, /^aion_owner_session=/)
  assert.match(cookie, /HttpOnly/)
  assert.match(cookie, /SameSite=Strict/)
  assert.doesNotMatch(cookie, /Secure/)

  const session = await route.GET(new Request("http://127.0.0.1:3001/api/aion/owner-session", {
    headers: { cookie },
  }))
  assert.deepEqual(await session.json(), { configured: true, authenticated: true })
})

for (const token of ["AION_OWNER_TOKEN=test-owner", 'AION_OWNER_TOKEN="test-owner"', "AION_OWNER_TOKEN='test-owner'"]) {
  test(`login accepts a complete owner-token assignment: ${token.slice(0, 16)}...`, async () => {
    const { login } = harness()
    assert.equal((await login("http://127.0.0.1:3001/api/aion/owner-session", token)).status, 200)
  })
}

for (const url of [
  "https://127.0.0.1:3001/api/aion/owner-session",
  "http://boardroom.example/api/aion/owner-session",
]) {
  test(`non-loopback-HTTP cookie stays secure: ${url}`, async () => {
    const { login } = harness()
    const response = await login(url)
    assert.match(response.headers.get("set-cookie"), /Secure/)
  })
}

test("loopback HTTP logout clears the usable cookie attributes", async () => {
  const { route } = harness()
  const response = await route.DELETE(new Request("http://localhost:3001/api/aion/owner-session", {
    method: "DELETE",
  }))
  const cookie = response.headers.get("set-cookie")

  assert.match(cookie, /HttpOnly/)
  assert.match(cookie, /SameSite=Strict/)
  assert.match(cookie, /Max-Age=0/)
  assert.doesNotMatch(cookie, /Secure/)
})

for (const body of [null, [], {}, { token: 42 }, { token: { value: 'test-owner' } }]) {
  test('malformed login payload returns 400 instead of crashing', async () => {
    const { route } = harness()
    const response = await route.POST(new Request('http://localhost:3000/api/aion/owner-session', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }))
    assert.equal(response.status, 400)
    assert.equal(response.headers.get('set-cookie'), null)
  })
}

test('wrong token never creates an owner session', async () => {
  const { login } = harness()
  const response = await login('http://localhost:3000/api/aion/owner-session', 'wrong')
  assert.equal(response.status, 403)
  assert.equal(response.headers.get('set-cookie'), null)
})

for (const headers of [{ host: 'boardroom.example' }, { host: 'invalid:port:authority' }, { host: 'localhost:3000', 'x-forwarded-proto': 'https' }]) {
  test('proxied or malformed public authority keeps the cookie secure', async () => {
    const { route } = harness()
    const response = await route.POST(new Request('http://localhost:3000/api/aion/owner-session', {
      method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: 'test-owner' }),
    }))
    assert.equal(response.status, 200)
    assert.match(response.headers.get('set-cookie'), /Secure/)
  })
}

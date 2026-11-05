import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const dependency = createRequire(import.meta.url)
const id = "0123456789abcdef0123456789abcdef"
const approval = {
  execution_request_id: id,
  capability: "runtime.syntax",
  requester_principal: "agent:local",
  decision: "pending",
  created_at: "2026-01-01T00:00:00+00:00",
  expires_at: "2026-01-01T00:05:00+00:00",
  decided_at: null,
  decided_by: null,
  consumed_at: null,
  consumed_by: null,
}

function harness(overrides = {}, upstream = () => Response.json(approval)) {
  const env = {
    AION_OWNER_TOKEN: "test-owner",
    AION_RUNTIME_MODE: "local",
    ...overrides,
  }
  const calls = []
  function load(path, dependencies = {}) {
    const loadedModule = { exports: {} }
    const code = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module: loadedModule, exports: loadedModule.exports,
      require: name => dependencies[name] ?? dependency(name),
      process: { env }, Buffer, URL, Response, AbortSignal,
      fetch: (...args) => { calls.push(args); return upstream(...args) },
    }, { filename: path })
    return loadedModule.exports
  }
  const session = load("lib/aion/owner-session.ts", {
    "./request-headers": load("lib/aion/request-headers.ts"),
  })
  const route = load("app/api/owner/runtime/syntax/approvals/[executionRequestId]/route.ts", {
    "@/lib/aion/owner-session": session,
  })
  const headers = {
    cookie: `aion_owner_session=${session.createOwnerSessionValue(60)}`,
    "X-AION-Request": "1",
    origin: "http://localhost:3000",
    "Content-Type": "application/json",
  }
  const request = (method, changes = {}, body = '{"approved":true}', path = id) => new Request(
    `http://localhost:3000/api/owner/runtime/syntax/approvals/${path}`,
    { method, headers: { ...headers, ...changes }, body: method === "POST" ? body : undefined },
  )
  const context = (executionRequestId = id) => ({ params: Promise.resolve({ executionRequestId }) })
  return { route, request, context, calls }
}

test("owner session gates review before it reaches runtime", async () => {
  const h = harness()
  assert.equal((await h.route.GET(h.request("GET", { cookie: "" }), h.context())).status, 401)
  assert.equal(h.calls.length, 0)
})

for (const [name, headers, body, status] of [
  ["missing CSRF header", { "X-AION-Request": "" }, '{"approved":true}', 403],
  ["cross-origin request", { origin: "https://untrusted.example" }, '{"approved":true}', 403],
  ["extra decision field", {}, '{"approved":true,"capability":"runtime.syntax"}', 400],
]) {
  test(`${name} cannot forward a decision`, async () => {
    const h = harness()
    assert.equal((await h.route.POST(h.request("POST", headers, body), h.context())).status, status)
    assert.equal(h.calls.length, 0)
  })
}

test("authorized review and decision forward only server-side owner authorization", async () => {
  const h = harness()
  const review = await h.route.GET(h.request("GET"), h.context())
  assert.deepEqual(await review.json(), approval)
  const decision = await h.route.POST(h.request("POST"), h.context())
  assert.deepEqual(await decision.json(), approval)
  assert.equal(h.calls.length, 2)
  assert.equal(h.calls[0][0].toString(), `http://127.0.0.1:8000/owner/runtime-syntax-approvals/${id}`)
  assert.equal(h.calls[0][1].headers.Authorization, "Bearer test-owner")
  assert.equal(h.calls[0][1].headers.cookie, undefined)
  assert.equal(h.calls[1][0].toString(), `http://127.0.0.1:8000/owner/runtime-syntax-approvals/${id}/decision`)
  assert.equal(h.calls[1][1].body, '{"approved":true}')
  assert.equal(h.calls[1][1].redirect, "error")
})

test("invalid IDs and non-loopback runtimes never receive authorization", async () => {
  const invalid = harness()
  assert.equal((await invalid.route.GET(invalid.request("GET"), invalid.context("x".repeat(32)))).status, 400)
  assert.equal(invalid.calls.length, 0)
  const untrusted = harness({ AION_RUNTIME_URL: "https://untrusted.example" })
  assert.equal((await untrusted.route.GET(untrusted.request("GET"), untrusted.context())).status, 503)
  assert.equal(untrusted.calls.length, 0)
})

test("runtime errors never expose upstream details", async () => {
  const h = harness({}, () => Response.json({ detail: "private runtime details" }, { status: 500 }))
  const response = await h.route.GET(h.request("GET"), h.context())
  assert.equal(response.status, 503)
  assert.deepEqual(await response.json(), { error: "Runtime syntax approvals are unavailable." })
})

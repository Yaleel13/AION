import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const dependency = createRequire(import.meta.url)
const id = "0123456789abcdef0123456789abcdef"
const event = { capability: "runtime.syntax", policy_decision: "allowed", event: "outcome", outcome: "succeeded", timestamp: "2026-11-03T00:00:00+00:00" }
function harness(upstream = () => Response.json({ request_id: id, events: [event] }), env = {}) {
  const calls = []
  function load(path, dependencies = {}) {
    const loadedModule = { exports: {} }
    const code = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module: loadedModule, exports: loadedModule.exports, require: name => dependencies[name] ?? dependency(name),
      process: { env: { AION_OWNER_TOKEN: "test-owner", ...env } }, Buffer, URL, Response, AbortSignal,
      fetch: (...args) => { calls.push(args); return upstream() },
    })
    return loadedModule.exports
  }
  const session = load("lib/aion/owner-session.ts", { "./request-headers": load("lib/aion/request-headers.ts") })
  const route = load("app/api/owner/audit/route.ts", {
    "@/lib/aion/owner-session": session,
    "@/lib/aion/runtime-correlation": load("lib/aion/runtime-correlation.ts"),
    "@/lib/aion/capability-audit": load("lib/aion/capability-audit.ts"),
  })
  const request = (authenticated = true, query = `request_id=${id}`) => new Request(`http://localhost:3000/api/owner/audit?${query}`, {
    headers: authenticated ? { cookie: `aion_owner_session=${session.createOwnerSessionValue(60)}` } : {},
  })
  return { route, request, calls }
}

test("known ID is a key, never authorization; anonymous requests never forward", async () => {
  const h = harness()
  assert.equal((await h.route.GET(h.request(false))).status, 401)
  assert.equal(h.calls.length, 0)
  const response = await h.route.GET(h.request())
  assert.equal(response.status, 200)
  const [url, init] = h.calls[0]
  assert.equal(url.pathname, "/owner/audit")
  assert.equal(url.searchParams.get("request_id"), id)
  assert.equal(init.headers.Authorization, "Bearer test-owner")
  assert.equal(init.headers.cookie, undefined)
  assert.equal(init.redirect, "error")
  assert.equal(response.headers.get("cache-control"), "no-store")
})
for (const query of ["", "request_id=malformed", `request_id=${"A".repeat(32)}`, `request_id=${id}&request_id=${id}`, `request_id=${id}&limit=999`]) {
  test(`invalid lookup never reaches runtime: ${query}`, async () => {
    const h = harness()
    assert.equal((await h.route.GET(h.request(true, query))).status, 400)
    assert.equal(h.calls.length, 0)
  })
}
test("projection strips raw details and all internal headers", async () => {
  const h = harness(() => Response.json({ request_id: id, output: "private output", events: [{ ...event, token: "test-owner", body: "private body", output: "private output" }] }, {
    headers: { Authorization: "Bearer test-owner", "Set-Cookie": "private cookie" },
  }))
  const response = await h.route.GET(h.request())
  assert.deepEqual(await response.json(), { request_id: id, events: [{ ...event, timestamp: "2026-11-03T00:00:00.000Z" }] })
  assert.equal(response.headers.get("authorization"), null)
  assert.equal(response.headers.get("set-cookie"), null)
})
test("missing records stay a successful empty lookup", async () => {
  const h = harness(() => Response.json({ request_id: id, events: [] }))
  assert.deepEqual(await (await h.route.GET(h.request())).json(), { request_id: id, events: [] })
})
for (const bad of [{ request_id: "b".repeat(32), events: [event] }, { request_id: id, events: [{ ...event, outcome: "private output" }] }, { request_id: id, events: [{ ...event, capability: ["runtime.syntax"] }] }]) {
  test("invalid upstream contract produces a generic structured error", async () => {
    const h = harness(() => Response.json(bad))
    const response = await h.route.GET(h.request())
    assert.equal(response.status, 502)
    assert.deepEqual(await response.json(), { error: "Audit lookup unavailable." })
  })
}
for (const upstream of [() => { throw new Error("private connection string") }, () => new Response("private body", { status: 500 })]) {
  test("runtime failures are unavailable without private details", async () => {
    const h = harness(upstream)
    const response = await h.route.GET(h.request())
    assert.equal(response.status, 503)
    assert.deepEqual(await response.json(), { error: "Audit lookup unavailable." })
  })
}
test("untrusted runtime URL never receives the owner bearer", async () => {
  const h = harness(undefined, { AION_RUNTIME_URL: "https://untrusted.example" })
  assert.equal((await h.route.GET(h.request())).status, 503)
  assert.equal(h.calls.length, 0)
})

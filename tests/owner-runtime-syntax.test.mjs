import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const loadDependency = createRequire(import.meta.url)

// Execute the actual route and session helper, with only the upstream transport
// replaced. This proves rejected requests never reach the runtime.
function harness(overrides = {}, upstream = async () => Response.json({
  ok: true, job: "runtime.syntax", status: "succeeded", output: "syntax valid",
})) {
  const env = { AION_OWNER_TOKEN: "test-owner", AION_RUNTIME_MODE: "local", ...overrides }
  const calls = []
  function load(path, dependencies = {}) {
    const loadedModule = { exports: {} }
    const code = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module: loadedModule, exports: loadedModule.exports,
      require: (name) => dependencies[name] ?? loadDependency(name),
      process: { env }, Buffer, URL, Response, AbortSignal,
      fetch: async (...args) => { calls.push(args); return upstream(...args) },
    }, { filename: path })
    return loadedModule.exports
  }
  const sharedHeaders = load("lib/aion/request-headers.ts")
  const session = load("lib/aion/owner-session.ts", { "./request-headers": sharedHeaders })
  const route = load("app/api/owner/runtime/syntax/route.ts", { "@/lib/aion/owner-session": session })
  const headers = {
    cookie: `aion_owner_session=${session.createOwnerSessionValue(60)}`,
    "X-AION-Request": "1", origin: "http://localhost:3000", "Content-Type": "application/json",
  }
  const request = (changes = {}, body = "{}", query = "") => new Request(`http://localhost:3000/api/owner/runtime/syntax${query}`, {
    method: "POST", headers: { ...headers, ...changes }, body,
  })
  return { route, request, calls }
}

for (const [name, headers, body, query, status] of [
  ["missing session", { cookie: "" }, "{}", "", 401],
  ["invalid session", { cookie: "aion_owner_session=invalid" }, "{}", "", 401],
  ["missing CSRF header", { "X-AION-Request": "" }, "{}", "", 403],
  ["cross-origin request", { origin: "https://untrusted.example" }, "{}", "", 403],
  ["missing origin", { origin: "" }, "{}", "", 403],
  ["wrong origin port", { host: "localhost:3000", origin: "http://localhost:3001" }, "{}", "", 403],
  ["wrong origin scheme", { host: "localhost:3000", origin: "https://localhost:3000" }, "{}", "", 403],
  ["argument override", {}, '{"argv":["unsafe"]}', "", 400],
  ["directory override", {}, "{}", "?cwd=/tmp", 400],
]) {
  test(`${name} cannot reach runtime`, async () => {
    const h = harness()
    assert.equal((await h.route.POST(h.request(headers, body, query))).status, status)
    assert.equal(h.calls.length, 0)
  })
}

test("authorized call forwards only the fixed job with a server-side token", async () => {
  const h = harness()
  const response = await h.route.POST(h.request())
  assert.equal(response.status, 200)
  assert.deepEqual(await response.json(), { ok: true, status: "succeeded", output: "syntax valid", truncated: false })
  assert.equal(h.calls.length, 1)
  const [url, init] = h.calls[0]
  assert.equal(url.toString(), "http://127.0.0.1:8000/local-executive/validate")
  assert.equal(init.method, "POST")
  assert.equal(init.body, "{}")
  assert.equal(init.headers.Authorization, "Bearer test-owner")
  assert.equal(init.redirect, "error")
  assert.equal(response.headers.get("Cache-Control"), "no-store")
})

test("non-loopback runtime never receives the token", async () => {
  const h = harness({ AION_RUNTIME_URL: "https://untrusted.example" })
  assert.equal((await h.route.POST(h.request())).status, 503)
  assert.equal(h.calls.length, 0)
})

test("same-origin check uses the incoming host when Next normalizes its URL", async () => {
  const h = harness()
  const response = await h.route.POST(h.request({ host: "127.0.0.1:3000", origin: "http://127.0.0.1:3000" }))
  assert.equal(response.status, 200)
  assert.equal(h.calls.length, 1)
})

test("non-local mode cannot forward a validation job", async () => {
  const h = harness({ AION_RUNTIME_MODE: "cloud" })
  assert.equal((await h.route.POST(h.request())).status, 503)
  assert.equal(h.calls.length, 0)
})

test("an upstream denial exposes neither the owner token nor upstream details", async () => {
  const h = harness({}, async () => Response.json({ detail: "private upstream details" }, { status: 403 }))
  const response = await h.route.POST(h.request())
  assert.equal(response.status, 503)
  const body = await response.text()
  assert.equal(body.includes("test-owner"), false)
  assert.equal(body.includes("private upstream details"), false)
})

test("disconnected runtime returns unavailable without leaking exception details", async () => {
  const h = harness({}, async () => { throw new Error("private upstream details") })
  const response = await h.route.POST(h.request())
  assert.equal(response.status, 503)
  assert.deepEqual(await response.json(), { status: "unavailable", error: "Local runtime unavailable." })
})

test("validation failure remains a failure result", async () => {
  const h = harness({}, async () => Response.json({ job: "runtime.syntax", ok: false, status: "failed", output: "SyntaxError" }))
  const result = await (await h.route.POST(h.request())).json()
  assert.equal(result.status, "failed")
  assert.equal(result.ok, false)
})

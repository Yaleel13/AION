import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const loadDependency = createRequire(import.meta.url)

function harness(overrides = {}, upstream = async () => Response.json({
  ok: true, job: "runtime.tests", status: "succeeded", duration_ms: 12,
})) {
  const env = { AION_OWNER_TOKEN: "test-owner", AION_RUNTIME_MODE: "local", ...overrides }
  const calls = []
  function load(path, dependencies = {}) {
    const module = { exports: {} }
    const code = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module, exports: module.exports,
      require: name => dependencies[name] ?? loadDependency(name),
      process: { env }, Buffer, URL, Response, AbortSignal,
      fetch: async (...args) => { calls.push(args); return upstream(...args) },
    }, { filename: path })
    return module.exports
  }
  const headers = load("lib/aion/request-headers.ts")
  const session = load("lib/aion/owner-session.ts", { "./request-headers": headers })
  const correlation = load("lib/aion/runtime-correlation.ts")
  const route = load("app/api/owner/runtime/tests/route.ts", {
    "@/lib/aion/owner-session": session, "@/lib/aion/runtime-correlation": correlation,
  })
  const request = (changes = {}, body = "{}", query = "") => new Request(`http://localhost:3000/api/owner/runtime/tests${query}`, {
    method: "POST",
    headers: {
      cookie: `aion_owner_session=${session.createOwnerSessionValue(60)}`,
      "X-AION-Request": "1",
      origin: "http://localhost:3000",
      "Content-Type": "application/json",
      ...changes,
    },
    body,
  })
  return { route, request, calls }
}

for (const [headers, body, query, status] of [
  [{ cookie: "" }, "{}", "", 401],
  [{ "X-AION-Request": "" }, "{}", "", 403],
  [{ origin: "https://untrusted.example" }, "{}", "", 403],
  [{}, '{"argv":["unsafe"]}', "", 400],
  [{}, "{}", "?timeout=1", 400],
]) {
  test(`invalid request cannot reach runtime (${status})`, async () => {
    const h = harness()
    assert.equal((await h.route.POST(h.request(headers, body, query))).status, status)
    assert.equal(h.calls.length, 0)
  })
}

test("authorized Boardroom test forwards only the fixed empty request", async () => {
  const h = harness()
  const response = await h.route.POST(h.request())
  assert.equal(response.status, 200)
  assert.deepEqual(await response.json(), { ok: true, status: "succeeded", duration_ms: 12 })
  assert.equal(h.calls.length, 1)
  const [url, init] = h.calls[0]
  assert.equal(url.toString(), "http://127.0.0.1:8000/local-executive/tests")
  assert.equal(init.body, "{}")
  assert.equal(init.headers.Authorization, "Bearer test-owner")
})

test("upstream output and credentials do not enter the Boardroom response", async () => {
  const h = harness({}, async () => Response.json({
    job: "runtime.tests", ok: false, status: "failed", duration_ms: 12,
    output: "private runtime output", token: "test-owner",
  }))
  const response = await h.route.POST(h.request())
  const body = await response.text()
  assert.equal(body.includes("private runtime output"), false)
  assert.equal(body.includes("test-owner"), false)
})

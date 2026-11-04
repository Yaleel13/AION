import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const loadDependency = createRequire(import.meta.url)

function harness(overrides = {}) {
  const env = {
    AION_OWNER_TOKEN: "terminal-owner-secret",
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
      module: loadedModule,
      exports: loadedModule.exports,
      require: name => dependencies[name] ?? loadDependency(name),
      process: { env },
      Buffer,
      URL,
      Request,
      Response,
      AbortSignal,
      fetch: async (...args) => {
        calls.push(args)
        const capability = JSON.parse(args[1].body).capability
        const summaries = {
          "project.inspect": "0123456",
          "git.status": "clean",
          "system.info": "linux inspection completed",
        }
        return Response.json({
          ok: true,
          capability,
          status: "succeeded",
          exit_code: 0,
          summary: summaries[capability] ?? null,
          stdout: "terminal-owner-secret",
          stderr: "private runtime output",
        })
      },
    }, { filename: path })
    return loadedModule.exports
  }
  const headers = load("lib/aion/request-headers.ts")
  const session = load("lib/aion/owner-session.ts", { "./request-headers": headers })
  const route = load("app/api/owner/terminal/diagnose/route.ts", {
    "@vercel/sandbox": { Sandbox: class {} },
    "@/lib/aion/owner-session": session,
  })
  const request = (changes = {}, body = '{"check":"inspect"}', origin = "http://localhost:3000") => new Request(
    "http://localhost:3000/api/owner/terminal/diagnose",
    {
      method: "POST",
      headers: {
        cookie: `aion_owner_session=${session.createOwnerSessionValue(60)}`,
        "X-AION-Request": "1",
        origin,
        "Content-Type": "application/json",
        ...changes,
      },
      body,
    },
  )
  return { route, request, calls }
}

for (const [name, headers, origin, status] of [
  ["missing session", { cookie: "" }, "http://localhost:3000", 401],
  ["missing CSRF marker", { "X-AION-Request": "" }, "http://localhost:3000", 403],
  ["cross origin", {}, "https://untrusted.example", 403],
  ["non-loopback local request", { host: "untrusted.example" }, "http://untrusted.example", 403],
]) {
  test(`${name} cannot reach the local runtime`, async () => {
    const h = harness()
    assert.equal((await h.route.POST(h.request(headers, '{"check":"inspect"}', origin))).status, status)
    assert.equal(h.calls.length, 0)
  })
}

test("authenticated Terminal forwards only the server bearer to loopback", async () => {
  const h = harness()
  const response = await h.route.POST(h.request())
  const body = await response.text()

  assert.equal(response.status, 200)
  assert.equal(h.calls.length, 3)
  for (const [url, init] of h.calls) {
    assert.equal(url.toString(), "http://127.0.0.1:8000/local-executive/execute")
    assert.equal(init.headers.Authorization, "Bearer terminal-owner-secret")
    assert.equal(init.redirect, "error")
  }
  assert.equal(body.includes("terminal-owner-secret"), false)
  assert.equal(body.includes("private runtime output"), false)
})

for (const runtimeUrl of [
  "https://untrusted.example",
  "http://owner:secret@127.0.0.1:8000",
  "http://127.0.0.1:8000/runtime",
  "http://127.0.0.1:8000?target=untrusted",
  "http://127.0.0.1:8000#fragment",
]) {
  test(`invalid runtime URL never receives the bearer: ${runtimeUrl}`, async () => {
    const h = harness({ AION_RUNTIME_URL: runtimeUrl })
    assert.equal((await h.route.POST(h.request())).status, 502)
    assert.equal(h.calls.length, 0)
  })
}

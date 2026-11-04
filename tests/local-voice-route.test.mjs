import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const loadDependency = createRequire(import.meta.url)

function loadVoiceRoute() {
  const loadedModule = { exports: {} }
  const code = ts.transpileModule(readFileSync("app/api/aion/voice/route.ts", "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  let fetchCalls = 0
  vm.runInNewContext(code, {
    module: loadedModule,
    exports: loadedModule.exports,
    require: name => loadDependency(name),
    process: { env: { AION_RUNTIME_MODE: "local" } },
    URL,
    Request,
    Response,
    AbortSignal,
    setTimeout,
    clearTimeout,
    fetch: async () => { fetchCalls += 1; throw new Error("must not run") },
  }, { filename: "app/api/aion/voice/route.ts" })
  return { route: loadedModule.exports, calls: () => fetchCalls }
}

test("local voice is unavailable without scoped authorization and never invokes the runtime", async () => {
  const h = loadVoiceRoute()
  const availability = await h.route.GET(new Request("http://localhost:3000/api/aion/voice"))
  const response = await h.route.POST(new Request("http://localhost:3000/api/aion/voice", {
    method: "POST",
    headers: { origin: "http://localhost:3000" },
  }))

  assert.deepEqual(await availability.json(), {
    available: false,
    reason: "scoped-voice-authorization-required",
  })
  assert.equal(response.status, 503)
  assert.deepEqual(await response.json(), {
    error: "Local voice is unavailable until scoped voice authorization is implemented.",
  })
  assert.equal(h.calls(), 0)
})

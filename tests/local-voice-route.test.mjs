import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"

const loadDependency = createRequire(import.meta.url)

function loadVoiceRoute() {
  function load(path, dependencies = {}) {
    const loadedModule = { exports: {} }
    const source = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(source, {
      module: loadedModule, exports: loadedModule.exports,
      require: name => dependencies[name] ?? loadDependency(name),
      process: { env: { AION_OWNER_TOKEN: "test-owner", AION_RUNTIME_MODE: "local" } },
      Buffer,
    }, { filename: path })
    return loadedModule.exports
  }
  const requestHeaders = load("lib/aion/request-headers.ts")
  const ownerSession = load("lib/aion/owner-session.ts", { "./request-headers": requestHeaders })
  const correlation = load("lib/aion/runtime-correlation.ts")
  const loadedModule = { exports: {} }
  const code = ts.transpileModule(readFileSync("app/api/aion/voice/route.ts", "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  let fetchCalls = 0
  vm.runInNewContext(code, {
    module: loadedModule,
    exports: loadedModule.exports,
    require: name => ({
      "@/lib/aion/owner-session": ownerSession,
      "@/lib/aion/runtime-correlation": correlation,
    })[name] ?? loadDependency(name),
    process: { env: { AION_OWNER_TOKEN: "test-owner", AION_RUNTIME_MODE: "local" } },
    Buffer, URL,
    Request,
    Response,
    AbortSignal,
    setTimeout,
    clearTimeout,
    fetch: async () => { fetchCalls += 1; throw new Error("must not run") },
  }, { filename: "app/api/aion/voice/route.ts" })
  return { route: loadedModule.exports, calls: () => fetchCalls }
}

test("local voice requires an owner session and never invokes the runtime on denial", async () => {
  const h = loadVoiceRoute()
  const availability = await h.route.GET(new Request("http://localhost:3000/api/aion/voice"))
  const response = await h.route.POST(new Request("http://localhost:3000/api/aion/voice", {
    method: "POST",
    headers: { origin: "http://localhost:3000", "Content-Type": "application/json" },
    body: "{}",
  }))

  assert.deepEqual(await availability.json(), { available: false })
  assert.equal(response.status, 401)
  assert.deepEqual(await response.json(), { error: "Owner authentication required." })
  assert.equal(h.calls(), 0)
})

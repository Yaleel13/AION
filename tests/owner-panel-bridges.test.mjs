import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { test } from "node:test"
import vm from "node:vm"
import ts from "typescript"
import nextConfig from "../next.config.mjs"

const dependency = createRequire(import.meta.url)
const names = ["acceptance", "capabilities", "operator-briefing", "outbound-gates", "sales-alerts", "moltbook-research", "moltbook-preparation", "moltbook-reviews", "moltbook-approvals", "commercial-execution"]

function bridge(name, upstream = () => Response.json({ ok: true })) {
  const calls = []
  const logs = []
  function load(path, dependencies = {}) {
    const loaded = { exports: {} }
    const code = ts.transpileModule(readFileSync(path, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module: loaded, exports: loaded.exports,
      require: name => dependencies[name] ?? dependency(name),
      process: { env: { AION_OWNER_TOKEN: "test-owner" } }, Buffer, Response, URL,
      console: { error: (...args) => logs.push(args) },
      fetch: async (...args) => { calls.push(args); return upstream() },
    })
    return loaded.exports
  }
  const headers = load("lib/aion/request-headers.ts")
  const session = load("lib/aion/owner-session.ts", { "./request-headers": headers })
  const upstreamBoundary = load("lib/aion/owner-upstream.ts")
  const route = load(`app/api/owner/${name}/route.ts`, {
    "@/lib/aion/owner-session": session, "@/lib/aion/owner-upstream": upstreamBoundary,
  })
  const request = (method, authenticated, csrf = true) => new Request(`http://127.0.0.1:3001/api/owner/${name}`, {
    method, headers: {
      ...(authenticated ? { cookie: `aion_owner_session=${session.createOwnerSessionValue(60)}` } : {}),
      ...(csrf ? headers.AION_REQUEST_HEADER : {}),
    }, ...(method === "POST" ? { body: "{}" } : {}),
  })
  return { route, request, calls, logs }
}

for (const name of names) {
  test(`${name}: authorized read forwards only the server bearer; anonymous read never forwards`, async () => {
    const h = bridge(name)
    const denied = await h.route.GET(h.request("GET", false))
    assert.equal(denied.status, 401)
    assert.equal(h.calls.length, 0)
    const allowed = await h.route.GET(h.request("GET", true))
    assert.equal(allowed.status, 200)
    assert.equal(h.calls.length, 1)
    const [url, init] = h.calls[0]
    assert.equal(url.pathname, `/api/internal/${name}`)
    assert.equal(init.headers.Authorization, "Bearer test-owner")
    assert.equal(init.headers.cookie, undefined)
    assert.equal(init.redirect, "error")
    assert.equal((await allowed.text()).includes("test-owner"), false)
  })
  test(`${name}: non-JSON upstream failures are structured and never expose raw bodies`, async () => {
    const h = bridge(name, () => new Response("private upstream content", { status: 500 }))
    const response = await h.route.GET(h.request("GET", true))
    assert.equal(response.status, 502)
    assert.deepEqual(await response.json(), { error: "Owner runtime is temporarily unavailable." })
    assert.equal(JSON.stringify(h.logs).includes("private upstream content"), false)
  })
  test(`${name}: disconnected upstream produces a structured unavailable response`, async () => {
    const h = bridge(name, () => { throw new Error("private connection details") })
    const response = await h.route.GET(h.request("GET", true))
    assert.equal(response.status, 503)
    assert.deepEqual(await response.json(), { error: "Owner runtime is temporarily unavailable." })
  })
  test(`${name}: server-side diagnostic details are not forwarded`, async () => {
    const h = bridge(name, () => Response.json({ detail: "private connection details" }, { status: 500 }))
    const response = await h.route.GET(h.request("GET", true))
    assert.equal(response.status, 500)
    assert.deepEqual(await response.json(), { error: "Owner runtime is temporarily unavailable." })
  })
  if (!['acceptance', 'capabilities', 'operator-briefing'].includes(name)) {
    test(`${name}: POST authorization and CSRF precede forwarding`, async () => {
      const h = bridge(name)
      assert.equal((await h.route.POST(h.request("POST", false))).status, 401)
      assert.equal((await h.route.POST(h.request("POST", true, false))).status, 403)
      assert.equal(h.calls.length, 0)
      assert.equal((await h.route.POST(h.request("POST", true))).status, 200)
      assert.equal(h.calls.length, 1)
      assert.equal(h.calls[0][1].method, "POST")
    })
  }
}

test("acceptance exposes a specific missing-Postgres state through its existing error contract", async () => {
  const h = bridge("acceptance", () => Response.json({ detail: "Durable Postgres is not configured" }, { status: 503 }))
  const response = await h.route.GET(h.request("GET", true))
  assert.equal(response.status, 503)
  assert.deepEqual(await response.json(), { error: "Durable Postgres is not configured" })
})

test("acceptance never logs an upstream HTML response body", async () => {
  const h = bridge("acceptance", () => new Response("private upstream content", { status: 404 }))
  await h.route.GET(h.request("GET", true))
  assert.equal(JSON.stringify(h.logs).includes("private upstream content"), false)
})

test("local rewrites expose only the reviewed exact paths, including the authenticated conversation alias", async () => {
  const previous = process.env.AION_RUNTIME_MODE
  const previousUrl = process.env.AION_RUNTIME_URL
  try {
    process.env.AION_RUNTIME_MODE = "local"
    process.env.AION_RUNTIME_URL = "http://127.0.0.1:8000"
    const local = await nextConfig.rewrites()
    const internal = local.filter(route => route.source.startsWith("/api/internal/"))
    assert.deepEqual(internal.map(route => route.source).sort(), [...names, 'conversation'].map(name => '/api/internal/'+name).sort())
    for (const route of internal) {
      assert.equal(route.source.includes(":"), false)
      assert.equal(route.destination, "http://127.0.0.1:8000" + route.source)
    }
    process.env.AION_RUNTIME_MODE = "cloud"
    assert.equal((await nextConfig.rewrites()).some(route => route.source.startsWith("/api/internal/")), false)
  } finally {
    if (previous === undefined) delete process.env.AION_RUNTIME_MODE
    else process.env.AION_RUNTIME_MODE = previous
    if (previousUrl === undefined) delete process.env.AION_RUNTIME_URL
    else process.env.AION_RUNTIME_URL = previousUrl
  }
})

test("the local browser-memory bridge supplies only the server credential to the guarded alias", async () => {
  const calls = []
  for (const configured of [true, false]) {
    const loaded = { exports: {} }
    const code = ts.transpileModule(readFileSync('app/api/aion/memory/route.ts','utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    vm.runInNewContext(code, {
      module: loaded, exports: loaded.exports, Response, URL,
      process: { env: { AION_RUNTIME_MODE:'local', ...(configured ? {AION_OWNER_TOKEN:'test-owner'} : {}) } },
      fetch: async (url, init) => { calls.push({url, init}); return Response.json({found:false,messages:[]}) },
    })
    const response = await loaded.exports.POST(new Request('http://127.0.0.1:3001/api/aion/memory',{
      method:'POST',body:JSON.stringify({clientSessionId:'test-client-session-0001'}),
    }))
    assert.equal(response.status, configured ? 200 : 503)
  }
  assert.equal(calls.length,1)
  assert.equal(calls[0].url.pathname,'/api/internal/conversation')
  assert.equal(calls[0].init.headers.Authorization,'Bearer test-owner')
})

test("the owner memory inspector authenticates before its read-only internal POST", async () => {
  const h = bridge('memory')
  assert.equal((await h.route.GET(h.request('GET',false))).status,401)
  assert.equal(h.calls.length,0)
  assert.equal((await h.route.GET(h.request('GET',true))).status,200)
  assert.equal(h.calls[0][0].pathname,'/api/internal/conversation')
  assert.equal(JSON.parse(h.calls[0][1].body).action,'facts')
  assert.equal(h.calls[0][1].headers.Authorization,'Bearer test-owner')
})

test("the owner memory inspector returns structured errors without upstream content", async () => {
  const h = bridge('memory',()=>new Response('private upstream content',{status:500}))
  const response=await h.route.GET(h.request('GET',true))
  assert.equal(response.status,502)
  const body=await response.json()
  assert.equal(typeof body.error,'string')
  assert.equal(body.error.includes('private upstream content'),false)
})

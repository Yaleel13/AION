import { WebMcpPublicDemo } from "@/components/webmcp-public-demo"

const samples = [
  ["demo-google-agentic", "Google agentic hackathon", "Low risk", "Strong fit"],
  ["demo-open-source-bounty", "Open-source AI tooling bounty", "Low risk", "Strong fit"],
  ["demo-web3-dev-contract", "Web3 developer contract", "Medium risk", "Review"],
  ["demo-upfront-fee", "Upfront-fee qualification offer", "High risk", "Reject"],
]

export default function WebMcpDemoPage() {
  return (
    <main className="mx-auto min-h-dvh w-full max-w-5xl px-5 py-12 sm:px-8">
      <WebMcpPublicDemo />
      <div className="mb-10 max-w-3xl">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">AION · WebMCP Challenge Demo</p>
        <h1 className="mt-3 font-serif text-4xl font-light tracking-tight text-foreground sm:text-5xl">Opportunity Review, made agent-native.</h1>
        <p className="mt-4 text-sm leading-7 text-muted-foreground">This public judge route exposes synthetic opportunity data through three read-only WebMCP tools. It demonstrates the same human-agent review pattern as AION without exposing owner memory, credentials, approvals, outbound messaging, wallets, payments, or trading.</p>
      </div>

      <section className="grid gap-3 sm:grid-cols-3">
        {[['demo_list_opportunities', 'Discover the bounded synthetic opportunity set.'], ['demo_rank_opportunities', 'Rank by value, credibility, fit, urgency, effort, and safety.'], ['demo_get_opportunity', 'Inspect one opportunity and its evidence-oriented fields.']].map(([name, description]) => (
          <article key={name} className="rounded-2xl border border-border bg-surface/50 p-4">
            <code className="text-xs text-gold">{name}</code>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
          </article>
        ))}
      </section>

      <section className="mt-8 rounded-2xl border border-border bg-surface/40 p-5">
        <h2 className="text-sm font-medium text-foreground">Synthetic judge dataset</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-muted-foreground"><tr><th className="pb-3">ID</th><th className="pb-3">Opportunity</th><th className="pb-3">Risk</th><th className="pb-3">Expected decision</th></tr></thead>
            <tbody>{samples.map(([id, title, risk, decision]) => <tr key={id} className="border-t border-border/70"><td className="py-3 font-mono text-xs text-muted-foreground">{id}</td><td className="py-3 text-foreground">{title}</td><td className="py-3 text-muted-foreground">{risk}</td><td className="py-3 text-muted-foreground">{decision}</td></tr>)}</tbody>
          </table>
        </div>
      </section>

      <section className="mt-8 rounded-2xl border border-gold/30 bg-gold/5 p-5">
        <h2 className="text-sm font-medium text-gold">Suggested agent test</h2>
        <p className="mt-2 text-sm leading-6 text-foreground/90">Ask your agent: “Use the WebMCP tools on this page to list the opportunities, rank them, and explain why the upfront-fee offer should not be pursued.”</p>
        <p className="mt-3 text-xs leading-5 text-muted-foreground">The page is intentionally non-destructive. Every exposed tool is read-only and operates only on static synthetic records.</p>
      </section>
    </main>
  )
}

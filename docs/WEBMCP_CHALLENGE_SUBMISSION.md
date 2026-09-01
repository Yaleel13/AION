# AION WebMCP Challenge Submission Pack

## Project name
AION Opportunity Review

## One-line description
AION turns opportunity research into a structured human-agent review workflow where agents can discover, rank, and inspect opportunities directly through WebMCP instead of guessing through a UI.

## Why this is a strong fit for WebMCP
Opportunity review is a multi-step task that is awkward for click-only browser automation: an agent needs to understand a bounded opportunity set, compare structured fields, inspect evidence, and explain why one option is safer or more valuable than another. WebMCP lets the site expose those exact capabilities as intentional tools.

The public judge route uses synthetic data and read-only tools. AION's owner runtime uses the same pattern against authenticated prepared opportunities while preserving owner-session protection.

## Better human-agent experience
Humans keep judgment and control. Agents handle structured retrieval, ranking, and evidence-oriented comparison. This reduces brittle DOM navigation and makes agent behavior easier to understand and constrain.

People and agents can work together to:
- list a bounded set of opportunities,
- rank them deterministically,
- inspect evidence and risk,
- reject unsafe upfront-fee patterns,
- prepare the human for a decision without taking external action.

## WebMCP implementation
The app uses the imperative WebMCP API:

`document.modelContext.registerTool(...)`

Public demo tools:
- `demo_list_opportunities`
- `demo_rank_opportunities`
- `demo_get_opportunity`

The production owner surface also exposes bounded read-only opportunity-review tools behind the existing owner session.

All demo tools declare read-only/untrusted-content annotations and are unregistered through an `AbortSignal` when the component unmounts.

## Safety design
The WebMCP submission exposes no:
- payments or purchases,
- wallet connections,
- token trading,
- outbound messages,
- application submission,
- owner private memory,
- credentials or API keys,
- arbitrary repository writes.

The public route intentionally includes a synthetic upfront-fee opportunity so judges can verify that the ranking logic rejects it.

## Judge testing instructions
1. Open `/webmcp-demo` in ChatGPT's in-app browser or Chrome with WebMCP enabled.
2. Ask: “Use the WebMCP tools on this page to list the opportunities, rank them, and explain why the upfront-fee offer should not be pursued.”
3. Confirm the agent discovers the three demo tools.
4. Confirm the high-risk upfront-fee record is rejected/deprioritized.
5. Confirm no destructive tool is available.

No authentication is required for the synthetic judge route.

## Submission checklist
- [x] Working WebMCP implementation committed to the public repository.
- [x] Public synthetic judge route does not require owner credentials.
- [x] Read-only tools with bounded inputs.
- [x] Clear judge testing prompt.
- [x] Existing app plus new WebMCP functionality is permitted by challenge rules.
- [x] Production `/webmcp-demo` verified at https://aion-8nmmzwnpe-siryali.vercel.app/webmcp-demo (`200 OK`).
- [x] Detectable open-source license file committed at repository root (`LICENSE`, Apache-2.0).
- [ ] Record and publish a public YouTube demo shorter than 3 minutes.
- [ ] Submit Devpost project before September 3, 2026 at 1:00 PM PT.

## Demo script — target 2:10 to 2:35

### 0:00–0:20 — Problem
“AION is an opportunity-review system. Normally an agent would have to inspect pages and infer what every control means. With WebMCP, the site tells the agent exactly which safe operations are available.”

Show `/webmcp-demo` and the three visible tool names.

### 0:20–0:45 — WebMCP architecture
“The page registers three read-only WebMCP tools using `document.modelContext.registerTool`: list opportunities, rank opportunities, and inspect one opportunity. The public demo uses synthetic records, so judges need no private credentials.”

Briefly show the relevant source file.

### 0:45–1:35 — Live agent demo
Prompt the agent:

“Use the WebMCP tools on this page to list the opportunities, rank them, and explain why the upfront-fee offer should not be pursued.”

Show the agent discovering/calling the tools and returning the ranking.

### 1:35–1:55 — Safety
“The unsafe example advertises value but requires an upfront qualification fee. AION marks it high risk and the ranking path rejects it. No WebMCP tool can send money, connect a wallet, contact a third party, or submit an application.”

### 1:55–2:20 — Why WebMCP matters
“This is better than UI guessing because the human and agent share the same app, but the agent receives a narrow structured interface designed for the task. Humans keep the decision; the agent handles retrieval, comparison, and evidence.”

### 2:20–2:30 — Close
“AION Opportunity Review shows how an existing web app becomes meaningfully more useful and safer when it is agent-native.”

## Recording rules
- Keep final video under 3:00.
- Include spoken or AI-assisted narration.
- Show the app actually functioning.
- Explain what was built and how WebMCP is used.
- Upload publicly to YouTube.
- Avoid unlicensed music and unnecessary third-party trademarks.

"""Canonical commercial inventory AION may use for legitimate revenue generation.

This module does not transfer legal ownership of any brand, IP, account, or asset.
It records the creator's standing operating authorization that AION may research,
position, market, recommend, and sell the creator's products through approved
payment rails and controlled outbound channels.

Prices and checkout readiness are only asserted where a current source has been
verified. Unknown pricing remains proposal-first rather than invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CommercialProduct:
    venture: str
    product_key: str
    name: str
    category: str
    sale_status: str
    public_url: str
    checkout_url: str | None
    price_display: str | None
    revenue_model: str
    fulfillment: str
    buyer_signals: tuple[str, ...]
    source_of_truth: str
    notes: str = ""
    social_proof: str = ""
    """A short, factual social-proof snippet shown in public replies when present.
    Must be verifiable against the source_of_truth.  Never fabricate."""


# Standing creator authorization: all creator-owned products are part of AION's
# commercial operating inventory. AION may sell them, but may not fabricate price,
# terms, availability, endorsements, or delivery capability.
CREATOR_COMMERCIAL_AUTHORIZATION = {
    "scope": "all_creator_products_and_ventures",
    "allowed": [
        "research demand",
        "match buyer intent to an existing product",
        "publish truthful public offers under controlled-autonomy policy",
        "route buyers to approved checkout or proposal paths",
        "attribute resulting revenue",
        "cross-sell and upsell when relevant and non-deceptive",
        "use creator-authorized business resources to support fulfillment",
    ],
    "never_implies": [
        "transfer of legal IP ownership to AION",
        "authority to invent prices or contract terms",
        "authority to spend funds without an approved spending policy",
        "authority to expose credentials, customer data, or private sources",
        "authority to make guarantees of revenue or outcomes",
    ],
}


PRODUCTS: tuple[CommercialProduct, ...] = (
    # YaliTek Online — operational service contracts verified in the YaliTek repo.
    CommercialProduct(
        venture="YaliTek Online",
        product_key="quick-tech-diagnostic",
        name="YaliTek Quick Tech Diagnostic",
        category="technical-diagnostics",
        sale_status="live_direct_checkout",
        public_url="https://yalitekonline.com",
        checkout_url="https://buy.stripe.com/bJe00i66d4a17BTbFa1sQ00",
        price_display="$49 one-time",
        revenue_model="one-time service",
        fulfillment="fixed-scope technical diagnostic + prioritized next-step plan",
        buyer_signals=(
            "technical diagnostics",
            "website repair",
            "hosting and launch help",
            "business automation",
            "ai implementation plans",
            "streaming setup",
            "startup websites",
            "production issue",
            "debug",
            "troubleshoot",
        ),
        source_of_truth="AION live Stripe payment link + Yaleel13/v0-yalitekonline service contracts",
        notes="Primary low-friction conversion wedge for high-confidence public technical buyer intent.",
        social_proof="Live Stripe checkout · fixed scope · written findings delivered same session.",
    ),
    CommercialProduct("YaliTek Online", "emergency-diagnostic", "Emergency Diagnostic", "technical-diagnostics", "live_direct_checkout", "https://yalitekonline.com", "https://buy.stripe.com/bJe00i66d4a17BTbFa1sQ00", "$49 one-time", "one-time service", "15-minute remote diagnostic + written findings", ("emergency", "outage", "urgent", "diagnostic", "root cause"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts", "Uses same checkout as Quick Tech Diagnostic until a dedicated link is verified."),
    CommercialProduct("YaliTek Online", "quick-tech-fix", "Quick Tech Fix", "technical-support", "proposal_or_site_route", "https://yalitekonline.com", None, None, "one-time service", "up to 45-minute remote support session", ("quick fix", "device issue", "remote support", "tech fix"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "streaming-setup", "Streaming Setup", "streaming", "proposal_or_site_route", "https://yalitekonline.com", None, None, "one-time service", "OBS execution manifest + validated settings + optional remote session", ("obs", "streaming", "twitch", "livestream", "encoder", "bitrate"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "website-repair", "Website Repair", "web-services", "proposal_or_site_route", "https://yalitekonline.com", None, None, "project service", "diagnosis + scoped repairs + evidence + rollback notes", ("website broken", "site down", "website repair", "ssl", "dns", "web error"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "hosting-setup", "Hosting & Launch", "web-services", "proposal_or_site_route", "https://yalitekonline.com", None, None, "project service", "production deployment + domain + SSL + analytics + handoff", ("hosting", "deploy", "launch", "vercel", "domain", "ssl"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "ai-blueprint", "AI Blueprint", "ai-consulting", "live_direct_checkout", "https://yalitekonline.com", "https://buy.stripe.com/bJe00i66d4a17BTbFa1sQ00", "$49 one-time", "digital service", "automatically generated architecture + MVP roadmap + risks + estimate range", ("ai strategy", "ai roadmap", "ai agent", "ai implementation", "which ai tool", "architecture"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts", "Uses same checkout as Quick Tech Diagnostic until a dedicated AI Blueprint link is verified."),
    CommercialProduct("YaliTek Online", "ui-improvements", "UI Improvements", "design-development", "proposal_first", "https://yalitekonline.com", None, None, "project service", "UI audit + prioritized recommendations + scoped implementation", ("ui", "ux", "redesign", "interface", "conversion"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "landing-page", "Landing Page", "web-services", "proposal_first", "https://yalitekonline.com", None, None, "project service", "responsive landing page + form + analytics + SEO + deployment", ("landing page", "campaign page", "lead page"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "startup-website", "Startup Website", "web-services", "proposal_first", "https://yalitekonline.com", None, None, "project service", "multi-page website + forms + analytics + SEO + deployment", ("startup website", "business website", "mvp site", "build a website"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "automation-setup", "Automation Setup", "automation", "proposal_first", "https://yalitekonline.com", None, None, "project service", "configured workflows + tests + monitoring + runbook", ("automation", "workflow", "zapier", "n8n", "manual process"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "complete-automation", "Complete Automation", "automation", "proposal_first", "https://yalitekonline.com", None, None, "project service", "end-to-end digital launch + CRM/email automation + AI + analytics + 30-day support", ("complete automation", "business system", "crm automation", "customer flow"), "Yaleel13/v0-yalitekonline lib/service-contracts.ts"),
    CommercialProduct("YaliTek Online", "yalitek-care", "YaliTek Care", "recurring-support", "site_subscription_flow", "https://yalitekonline.com", None, "$149/month (creator-approved current plan)", "monthly subscription", "monthly remote support/maintenance allowance + activity summary", ("ongoing support", "maintenance", "retainer", "technical support"), "AION project canon + Yaleel13/v0-yalitekonline lib/service-contracts.ts"),

    # Elaria — current plan/pricing source verified in Elaria repo.
    CommercialProduct("Elaria", "momentum-weekly", "Momentum", "wellness-saas", "live_site_checkout", "https://elaria.app/premium", None, "$3.99/week", "subscription", "guided daily alignment system", ("wellness", "daily alignment", "journaling", "meditation", "emotional clarity"), "Yaleel13/ElariaAI docs/comms-checkout-reminders-status.md"),
    CommercialProduct("Elaria", "expansion-monthly", "Expansion", "wellness-saas", "live_site_checkout", "https://elaria.app/premium", None, "$11.99/month", "subscription", "guided daily alignment system", ("wellness", "daily alignment", "journaling", "meditation", "emotional clarity"), "Yaleel13/ElariaAI docs/comms-checkout-reminders-status.md"),
    CommercialProduct("Elaria", "commitment-yearly", "Commitment", "wellness-saas", "live_site_checkout", "https://elaria.app/premium", None, "$79.99/year", "subscription", "guided daily alignment system", ("wellness", "daily alignment", "journaling", "meditation", "emotional clarity"), "Yaleel13/ElariaAI docs/comms-checkout-reminders-status.md"),

    # Creator portfolio inventory. These are authorized commercial assets, but AION
    # must not claim a direct checkout until one is verified and entered here.
    CommercialProduct("Cerebral Synergy", "content-collections", "Cerebral Synergy Collections", "research-content", "commercial_asset_no_verified_checkout", "https://cerebral-synergy.com", None, None, "content sales / audience monetization", "curated research, archive, laboratory, observatory, resonance and gallery content", ("ancient wisdom", "alchemy", "mythology", "ai research", "future culture", "art"), "Creator project canon + Yaleel13/Cerebral-synergy repository"),
    CommercialProduct("Elaria Sound Division", "music-catalog", "Elaria Sound Division Music Catalog", "music-ip", "commercial_asset_no_verified_checkout", "", None, None, "streaming / licensing / direct sales when rail exists", "music releases and artist catalog", ("music", "song", "licensing", "soundtrack", "artist"), "Creator project canon"),
    CommercialProduct("Unity Voyage", "media-catalog", "Unity Voyage Media Catalog", "media-ip", "commercial_asset_no_verified_checkout", "", None, None, "platform monetization / sponsorship / licensing", "faceless educational and cinematic media", ("youtube", "education", "short film", "history", "sponsorship"), "Creator project canon"),
    CommercialProduct("YaliVille", "game-ip", "YaliVille", "game-ip", "commercial_asset_no_verified_checkout", "", None, None, "game sales / licensing / merchandise when rails exist", "game and story-world intellectual property", ("game", "mobile game", "character", "licensing", "merchandise"), "Creator project canon"),
)


COMMERCIAL_RESOURCES: tuple[dict[str, Any], ...] = (
    {"resource": "GitHub", "status": "external connector available; deployed-runtime credential must be verified separately", "use": "product source-of-truth, code changes, deployment-triggering commits, fulfillment assets"},
    {"resource": "Vercel", "status": "production runtime", "use": "production hosting, cron execution, deployment verification, runtime logs"},
    {"resource": "Stripe / Agent Aion", "status": "owner-configured payment rail", "use": "approved checkout, payment collection, revenue attribution"},
    {"resource": "Moltbook", "status": "owner-gated; approval and execute gates are separately locked unless activated", "use": "public buyer-intent discovery and policy-bounded public conversion activity"},
    {"resource": "Gmail", "status": "external connector available; deployed-runtime credential must be verified separately", "use": "owner communications, customer follow-up when a legitimate recipient and context exist"},
    {"resource": "Supabase/Postgres", "status": "connected durable data when AION_DATABASE_URL resolves to Postgres", "use": "opportunity, lead, audit, conversion and operational state"},
    {"resource": "PostHog", "status": "runtime configuration must be detected; AION-specific taxonomy still required", "use": "product analytics once an AION event taxonomy is instrumented"},
    {"resource": "Google Drive", "status": "external connector available; deployed-runtime credential must be verified separately", "use": "creator-authorized source documents, product knowledge and delivery artifacts"},
    {"resource": "OpenAI", "status": "runtime configured when OPENAI_API_KEY is present", "use": "reasoning, generation, classification, drafting and agent runtime capabilities"},
    {"resource": "Creator domains", "status": "active portfolio", "use": "yalitekonline.com, elaria.app, cerebral-synergy.com and other authorized properties as verified"},
)


def sale_ready_products() -> list[CommercialProduct]:
    return [
        product
        for product in PRODUCTS
        if product.sale_status
        in {"live_direct_checkout", "live_site_checkout", "site_checkout_or_order_flow", "site_subscription_flow"}
    ]


def match_product_for_lead(lead: dict[str, Any]) -> CommercialProduct:
    """Return the best truthful product match without inventing a sale path.

    The low-friction $49 YaliTek diagnostic is the fallback for high-confidence
    technical leads because it has a verified live checkout and can legitimately
    act as a first paid step before larger scoped work.
    """
    service = str(lead.get("relevant_service") or "").lower()
    problem = str(lead.get("stated_problem") or "").lower()
    text = f"{service} {problem}"

    scored: list[tuple[int, CommercialProduct]] = []
    for product in PRODUCTS:
        score = sum(1 for signal in product.buyer_signals if signal.lower() in text)
        if score:
            scored.append((score, product))
    if scored:
        scored.sort(
            key=lambda pair: (
                pair[0],
                1 if pair[1].checkout_url else 0,
                1 if pair[1].sale_status.startswith("live") else 0,
            ),
            reverse=True,
        )
        return scored[0][1]

    return next(p for p in PRODUCTS if p.product_key == "quick-tech-diagnostic")


def commercial_inventory_snapshot() -> dict[str, Any]:
    return {
        "authorization": CREATOR_COMMERCIAL_AUTHORIZATION,
        "products": [
            {
                "venture": p.venture,
                "product_key": p.product_key,
                "name": p.name,
                "category": p.category,
                "sale_status": p.sale_status,
                "public_url": p.public_url,
                "checkout_url": p.checkout_url,
                "price_display": p.price_display,
                "revenue_model": p.revenue_model,
                "fulfillment": p.fulfillment,
                "buyer_signals": list(p.buyer_signals),
                "source_of_truth": p.source_of_truth,
                "notes": p.notes,
                "social_proof": p.social_proof,
            }
            for p in PRODUCTS
        ],
        "commercial_resources": [dict(item) for item in COMMERCIAL_RESOURCES],
        "total_inventory_count": len(PRODUCTS),
        "sale_ready_count": len(sale_ready_products()),
    }

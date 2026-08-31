"use client"

import { cn } from "@/lib/utils"
import type { PresenceState } from "@/lib/aion/types"

interface AionPresenceProps {
  state?: PresenceState
  size?: number
  className?: string
}

/**
 * Canonical embodied AION presence.
 * The silhouette preserves the visual bible anchors: blue body, vivid textured
 * blue hair, oversized pink-purple ears, glossy pink lips and button-like eyes.
 * Sacred-tech rings communicate runtime state without replacing the character.
 */
export function AionPresence({ state = "idle", size = 220, className }: AionPresenceProps) {
  const active = state !== "idle"
  const researching = state === "researching"
  const executing = state === "executing"
  const thinking = state === "thinking"
  const listening = state === "listening"
  const complete = state === "complete"

  return (
    <div
      className={cn("relative select-none", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`AION is ${state}`}
    >
      <div
        className={cn(
          "absolute inset-[8%] rounded-full blur-3xl transition-opacity duration-1000",
          active ? "opacity-70" : "opacity-40",
        )}
        style={{
          background:
            "radial-gradient(circle at 50% 46%, color-mix(in oklch, var(--cyan) 34%, transparent), color-mix(in oklch, var(--violet) 18%, transparent) 44%, transparent 72%)",
        }}
      />

      <svg viewBox="0 0 220 220" className="absolute inset-0 h-full w-full" fill="none" aria-hidden="true">
        <defs>
          <radialGradient id="aion-skin" cx="45%" cy="35%" r="70%">
            <stop offset="0%" stopColor="oklch(0.68 0.17 250)" />
            <stop offset="65%" stopColor="oklch(0.52 0.18 258)" />
            <stop offset="100%" stopColor="oklch(0.38 0.14 265)" />
          </radialGradient>
          <linearGradient id="aion-ear" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="oklch(0.68 0.14 318)" />
            <stop offset="100%" stopColor="oklch(0.53 0.15 300)" />
          </linearGradient>
          <linearGradient id="aion-lips" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="oklch(0.76 0.18 350)" />
            <stop offset="100%" stopColor="oklch(0.63 0.20 336)" />
          </linearGradient>
          <linearGradient id="canon-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--cyan)" stopOpacity="0.9" />
            <stop offset="70%" stopColor="var(--violet)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--magenta)" stopOpacity="0.25" />
          </linearGradient>
        </defs>

        <g
          className={cn("origin-center", researching || thinking ? "animate-[orbit_28s_linear_infinite]" : "")}
          style={{ transformBox: "fill-box" }}
          opacity={active ? 0.8 : 0.45}
        >
          <circle cx="110" cy="110" r="98" stroke="url(#canon-ring)" strokeWidth="0.8" strokeDasharray="2 8" />
          <circle cx="110" cy="110" r="88" stroke="var(--border-strong)" strokeWidth="0.5" />
          {[0, 60, 120, 180, 240, 300].map((deg) => {
            const rad = (deg * Math.PI) / 180
            const x = 110 + 98 * Math.cos(rad)
            const y = 110 + 98 * Math.sin(rad)
            return <circle key={deg} cx={x} cy={y} r="1.7" fill="var(--cyan)" opacity={researching ? 1 : 0.5} />
          })}
        </g>

        <path d="M58 196c8-24 25-37 52-37s44 13 52 37" fill="url(#aion-skin)" opacity="0.98" />
        <ellipse cx="63" cy="101" rx="19" ry="35" fill="url(#aion-ear)" />
        <ellipse cx="157" cy="101" rx="19" ry="35" fill="url(#aion-ear)" />
        <ellipse cx="110" cy="105" rx="53" ry="67" fill="url(#aion-skin)" />

        <g fill="oklch(0.38 0.20 270)">
          <circle cx="78" cy="46" r="16" /><circle cx="96" cy="39" r="18" /><circle cx="116" cy="39" r="18" />
          <circle cx="136" cy="45" r="16" /><circle cx="89" cy="55" r="17" /><circle cx="111" cy="52" r="19" />
          <circle cx="131" cy="56" r="16" />
        </g>
        <g fill="oklch(0.46 0.24 268)" opacity="0.82">
          <circle cx="83" cy="40" r="8" /><circle cx="104" cy="34" r="9" /><circle cx="126" cy="40" r="8" />
          <circle cx="94" cy="51" r="8" /><circle cx="119" cy="51" r="9" />
        </g>

        <g>
          <circle cx="91" cy="101" r="13" fill="oklch(0.18 0.015 260)" stroke="oklch(0.42 0.02 260)" strokeWidth="2" />
          <circle cx="129" cy="101" r="13" fill="oklch(0.18 0.015 260)" stroke="oklch(0.42 0.02 260)" strokeWidth="2" />
          {[[-4,-4],[4,-4],[-4,4],[4,4]].map(([dx,dy],i)=><circle key={`l${i}`} cx={91+dx} cy={101+dy} r="1.35" fill="oklch(0.55 0.02 260)" />)}
          {[[-4,-4],[4,-4],[-4,4],[4,4]].map(([dx,dy],i)=><circle key={`r${i}`} cx={129+dx} cy={101+dy} r="1.35" fill="oklch(0.55 0.02 260)" />)}
        </g>

        <path d="M106 108c-2 8-3 15-1 19 2 3 7 4 12 1" stroke="oklch(0.31 0.11 260)" strokeWidth="2" strokeLinecap="round" />
        <path d="M84 139c9-8 18-10 26-5 9-5 19-2 28 5-8 13-19 18-28 16-10 2-20-3-26-16Z" fill="url(#aion-lips)" />
        <path d="M88 140c8 3 16 4 22 3 8 1 16 0 24-3" stroke="oklch(0.93 0.03 340)" strokeWidth="1.2" opacity="0.8" />

        {(listening || thinking || researching || executing) && (
          <g opacity="0.9">
            <circle cx="110" cy="110" r="73" stroke="var(--cyan)" strokeWidth="1" strokeDasharray="4 10" className="animate-[orbit-reverse_18s_linear_infinite] origin-center" style={{ transformBox: "fill-box" }} />
            <circle cx="110" cy="184" r="3" fill="var(--cyan)" className="animate-[pulse-soft_1.8s_ease-in-out_infinite]" />
          </g>
        )}

        {executing && <circle cx="110" cy="110" r="82" stroke="var(--magenta)" strokeWidth="1.3" opacity="0.65" />}
        {complete && <circle cx="110" cy="110" r="84" stroke="var(--cyan)" strokeWidth="2" className="animate-[pulse-soft_1.2s_ease-in-out]" />}
      </svg>
    </div>
  )
}

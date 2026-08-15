"use client"

import { cn } from "@/lib/utils"
import type { PresenceState } from "@/lib/aion/types"

interface AionPresenceProps {
  state?: PresenceState
  size?: number
  className?: string
}

/**
 * AionPresence — an abstract luminous intelligence core.
 * Concentric rings, orbital nodes and faint alchemical geometry that
 * reorganize with AION's state. Not a face, not a brain, not a HUD:
 * an instrument of quiet cognition.
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
      {/* Soft ambient bloom */}
      <div
        className={cn(
          "absolute inset-0 rounded-full blur-2xl transition-opacity duration-1000",
          active ? "opacity-70" : "opacity-40",
        )}
        style={{
          background:
            "radial-gradient(circle at 50% 45%, color-mix(in oklch, var(--violet) 45%, transparent), transparent 62%)",
        }}
      />

      <svg
        viewBox="0 0 200 200"
        className="absolute inset-0 h-full w-full"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="core-fill" cx="50%" cy="45%" r="55%">
            <stop offset="0%" stopColor="oklch(0.95 0.03 90)" stopOpacity="0.95" />
            <stop offset="45%" stopColor="oklch(0.82 0.105 85)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="oklch(0.66 0.13 292)" stopOpacity="0.05" />
          </radialGradient>
          <linearGradient id="ring-stroke" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="oklch(0.82 0.105 85)" stopOpacity="0.9" />
            <stop offset="100%" stopColor="oklch(0.66 0.13 292)" stopOpacity="0.5" />
          </linearGradient>
        </defs>

        {/* Outer ring — orbital lines */}
        <g
          className={cn(
            "origin-center",
            researching || thinking ? "animate-[orbit_24s_linear_infinite]" : "",
          )}
          style={{ transformBox: "fill-box" }}
        >
          <circle cx="100" cy="100" r="88" stroke="var(--border-strong)" strokeWidth="0.5" opacity="0.6" />
          <circle
            cx="100"
            cy="100"
            r="88"
            stroke="url(#ring-stroke)"
            strokeWidth="1"
            strokeDasharray="2 10"
            opacity={active ? 0.8 : 0.35}
          />
        </g>

        {/* Alchemical geometry — two interlocked triangles, held quiet */}
        <g
          className={cn(
            "origin-center transition-opacity duration-700",
            thinking ? "animate-[orbit-reverse_32s_linear_infinite]" : "",
          )}
          style={{ transformBox: "fill-box" }}
          opacity={active ? 0.5 : 0.22}
        >
          <polygon points="100,32 158,140 42,140" stroke="url(#ring-stroke)" strokeWidth="0.6" />
          <polygon points="100,168 42,60 158,60" stroke="url(#ring-stroke)" strokeWidth="0.6" />
        </g>

        {/* Mid ring */}
        <g
          className={cn(
            "origin-center",
            researching ? "animate-[orbit-reverse_18s_linear_infinite]" : "",
          )}
          style={{ transformBox: "fill-box" }}
        >
          <circle cx="100" cy="100" r="62" stroke="url(#ring-stroke)" strokeWidth="1" opacity={active ? 0.9 : 0.4} />
          {/* Orbital nodes — activate when researching */}
          {[0, 90, 180, 270].map((deg) => {
            const rad = (deg * Math.PI) / 180
            const x = 100 + 62 * Math.cos(rad)
            const y = 100 + 62 * Math.sin(rad)
            return (
              <circle
                key={deg}
                cx={x}
                cy={y}
                r={researching ? 3 : 1.6}
                fill="var(--gold)"
                className={researching ? "animate-[pulse-soft_2.4s_ease-in-out_infinite]" : ""}
                opacity={researching ? 1 : 0.5}
              />
            )
          })}
        </g>

        {/* Inner ring — becomes active during execution */}
        <circle
          cx="100"
          cy="100"
          r="40"
          stroke={executing ? "var(--gold)" : "url(#ring-stroke)"}
          strokeWidth={executing ? "1.6" : "1"}
          opacity={active ? 0.95 : 0.5}
          className={executing ? "animate-[pulse-soft_1.8s_ease-in-out_infinite]" : ""}
        />

        {/* Listening waveform across the core */}
        {listening && (
          <g>
            {[-18, -9, 0, 9, 18].map((offset, i) => (
              <rect
                key={offset}
                x={100 + offset - 1.4}
                y={90}
                width="2.8"
                height="20"
                rx="1.4"
                fill="var(--gold)"
                style={{
                  transformOrigin: "center",
                  animation: `waveform ${0.9 + (i % 3) * 0.25}s ease-in-out infinite`,
                  animationDelay: `${i * 0.08}s`,
                }}
              />
            ))}
          </g>
        )}

        {/* Central core */}
        <circle
          cx="100"
          cy="100"
          r={listening ? 26 : 22}
          fill="url(#core-fill)"
          className={cn(
            !active && "animate-[breathe_6s_ease-in-out_infinite]",
            complete && "animate-[pulse-soft_1.2s_ease-in-out]",
          )}
        />
        <circle cx="100" cy="100" r="6" fill="oklch(0.97 0.02 90)" opacity="0.9" />
      </svg>
    </div>
  )
}

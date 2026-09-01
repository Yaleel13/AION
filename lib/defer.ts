/** Defer work until after the current effect commit (satisfies react-hooks/set-state-in-effect). */
export function defer(fn: () => void): void {
  queueMicrotask(fn)
}

/** Accept only the runtime's server-generated uuid4().hex representation. */
export function runtimeRequestId(value: string | null): string | undefined {
  return value?.length === 32 && /^[0-9a-f]{32}$/.test(value) ? value : undefined
}

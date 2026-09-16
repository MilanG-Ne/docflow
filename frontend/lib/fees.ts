/** Convert a decimal input without multiplying a binary floating-point value. */
export function hundredths(value: string): number | null {
  if (!/^\d{1,6}(\.\d{1,2})?$/.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}

/** Positive quantities use the API's per-line ROUND_HALF_UP rule. */
export function lineTotal(quantity: string, unitCents: number): number {
  const days = hundredths(quantity);
  return days === null ? 0 : Math.floor((days * unitCents + 50) / 100);
}

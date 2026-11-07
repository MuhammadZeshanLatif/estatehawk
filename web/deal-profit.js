// Estimates only. All amounts are USD; resale value and repair costs are user assumptions.
export function estimateDealProfit(v) {
  const purchase = Number(v.purchase), resale = Number(v.resale), repairs = Number(v.repairs);
  const closing = Number(v.closing), monthly = Number(v.monthly), months = Number(v.months);
  const sellingPercent = Number(v.sellingPercent), taxes = Number(v.taxes), target = Number(v.target);
  if (![purchase, resale, repairs, closing, monthly, months, sellingPercent, taxes, target].every(Number.isFinite) ||
      [purchase, repairs, closing, monthly, months, taxes, target].some((n) => n < 0) ||
      resale <= 0 || sellingPercent < 0 || sellingPercent >= 100 || months > 120) return null;
  const selling = resale * sellingPercent / 100;
  const holding = monthly * months;
  const costs = purchase + repairs + closing + holding + selling + taxes;
  const profit = resale - costs;
  return { selling, holding, costs, profit, roi: costs > 0 ? profit / costs * 100 : 0,
    maxOffer: resale - selling - repairs - closing - holding - taxes - target };
}

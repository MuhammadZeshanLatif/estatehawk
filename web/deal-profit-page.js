import { estimateDealProfit } from './deal-profit.js';

const form = document.getElementById('calc-form');
const results = document.getElementById('calc-results');
const status = document.getElementById('calc-status');
const fields = ['purchase', 'resale', 'repairs', 'closing', 'monthly', 'months', 'sellingPercent', 'taxes', 'target'];
const inputs = Object.fromEntries(fields.map((key) => [key, document.getElementById(`calc-${key}`)]));
const currency = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);

function update() {
  const values = Object.fromEntries(fields.map((key) => [key, inputs[key].value === '' ? NaN : Number(inputs[key].value)]));
  for (const key of fields) inputs[key].setAttribute('aria-invalid', String(inputs[key].value !== '' && !inputs[key].validity.valid));
  if (!inputs.purchase.value || !inputs.resale.value) {
    results.hidden = true;
    status.textContent = 'Enter a purchase price and expected resale value to see your estimate.';
    return;
  }
  const estimate = estimateDealProfit(values);
  if (!estimate || fields.some((key) => !inputs[key].validity.valid)) {
    results.hidden = true;
    status.textContent = 'Check your entries. Amounts must be non-negative, resale above zero, selling costs below 100%, and holding period at most 120 months.';
    return;
  }
  status.textContent = 'Estimate updated as you type.';
  results.hidden = false;
  const profit = document.getElementById('calc-profit');
  profit.textContent = currency(estimate.profit);
  profit.classList.toggle('negative', estimate.profit < 0);
  document.getElementById('calc-costs').textContent = currency(estimate.costs);
  document.getElementById('calc-holding').textContent = currency(estimate.holding);
  document.getElementById('calc-selling').textContent = currency(estimate.selling);
  document.getElementById('calc-roi').textContent = `${estimate.roi.toFixed(1)}%`;
  document.getElementById('calc-max').textContent = estimate.maxOffer < 0 ? 'Not feasible' : currency(estimate.maxOffer);
}

form.addEventListener('input', update);
form.addEventListener('reset', () => setTimeout(update, 0));
update();

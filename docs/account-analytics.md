# Point-in-Time Account Analytics (C.1)

`graph_engine.account_analytics.build_account_analytics` computes an independent
sidecar for one account from transaction mappings containing `step`, `amount`,
`name_orig`, and `name_dest` (or the PaySim aliases `nameOrig` and `nameDest`).
It does not read fraud labels, modify model features, persist results, or make
fraud predictions.

## Time and input semantics

- `step` is a non-negative integer-valued discrete step, not a timestamp.
- Only rows with `step <= cutoff_step` are considered. For rows after the
  cutoff, only `step` is validated; their counterparties and amounts are not
  inspected.
- A trailing window of `W` steps is the interval
  `(cutoff_step - W, cutoff_step]`; its start is exclusive and cutoff inclusive.
  The defaults are 1, 7, and 30 steps. The output includes each window size and
  both boundary values.
- Missing or invalid fields in an in-scope row raise `ValueError`. Amounts must
  be finite and non-negative. Rows not involving the requested account are
  ignored after their in-scope required fields have been validated.
- The function does not mutate its iterable or row mappings.

## Formulas and interpretation

- Inbound/outbound counts and amounts count destination/origin roles
  respectively. A self-transfer counts in both directional views, but once in
  the distinct in-scope transaction basis for `total_turnover` and
  `average_transaction_amount`. Average amount is total turnover divided by
  the number of distinct in-scope transactions involving the account.
- `inbound_to_outbound_amount_ratio` is inbound amount divided by outbound
  amount, or `null` when outbound amount is zero.
- First/last activity are the minimum/maximum observed steps. Activity span is
  `last - first` (elapsed discrete steps). Gap statistics are calculated between
  distinct sorted activity steps; multiple transactions in a step do not imply
  an order or an intra-step gap.
- Directional counterparty concentration excludes self-transfers, which have no
  distinct counterparty. Per-counterparty transaction and amount shares divide
  by the respective total among counterparties. HHI is the sum of squared
  shares; dominant share is the largest share. Amount shares, amount HHI, and
  dominant amount share are `null` if the counterparty amount total is zero.
- Empty-activity totals/counts are zero; undefined averages, ratios, timing,
  and concentration statistics are `null`.

These descriptive measurements indicate activity and concentration only. They
do not establish causal money movement, suspiciousness, or validated fraud
risk.

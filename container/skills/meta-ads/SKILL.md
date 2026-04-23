---
name: meta-ads
description: Read-only access to Meta Ads (Facebook/Instagram) performance via the Graph API. Use when the user asks about Meta Ads, Facebook Ads, Instagram Ads, campaign spend, ROAS, impressions, clicks, or ad performance.
---

# Meta Ads (read-only)

Query Facebook/Instagram ad performance via the Graph API using `$META_ADS_TOKEN`. Scope is `ads_read` — this skill only covers listing and insights, not mutations. If the user asks to pause, edit, or create a campaign, explain that the current token is read-only.

If `$META_ADS_TOKEN` is unset, tell the user to follow the setup at the bottom of this file.

`$META_ADS_ACCOUNT_ID` (format: `act_1234567890`) is the default account. If the user has multiple, confirm which one before querying.

## Smoke test

Run this first when the user asks anything Meta Ads related — it confirms the token still works:

```bash
curl -s "https://graph.facebook.com/v22.0/me/adaccounts?fields=id,name,currency&access_token=$META_ADS_TOKEN" | jq '.data[] | {id, name, currency}'
```

If it returns `{"error":{...}}` with code 190, the token was revoked or expired — stop and tell the user to regenerate it (see Setup).

## Ad accounts

### List

```bash
curl -s "https://graph.facebook.com/v22.0/me/adaccounts?fields=id,name,account_status,currency,timezone_name,amount_spent&access_token=$META_ADS_TOKEN" | jq '.data[] | {id, name, account_status, currency, amount_spent}'
```

### Details

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID?fields=id,name,account_status,currency,timezone_name,balance,amount_spent,spend_cap&access_token=$META_ADS_TOKEN" | jq
```

## Campaigns / ad sets / ads

### List campaigns

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/campaigns?fields=id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time&access_token=$META_ADS_TOKEN" | jq '.data[] | {id, name, status, objective, daily_budget}'
```

### Campaign details

```bash
curl -s "https://graph.facebook.com/v22.0/{campaign-id}?fields=id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time,created_time,updated_time&access_token=$META_ADS_TOKEN" | jq
```

### List ad sets

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/adsets?fields=id,name,status,campaign_id,daily_budget,lifetime_budget,start_time,end_time,targeting&access_token=$META_ADS_TOKEN" | jq '.data[] | {id, name, status, campaign_id, daily_budget}'
```

### List ads

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/ads?fields=id,name,status,adset_id,campaign_id,created_time&access_token=$META_ADS_TOKEN" | jq '.data[] | {id, name, status, adset_id}'
```

## Insights (performance)

Default fields worth pulling: `impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,actions,action_values`. Add `purchase_roas` if the user cares about ROAS.

### Account, last 7 days

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/insights?fields=impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,actions,purchase_roas&date_preset=last_7d&access_token=$META_ADS_TOKEN" | jq '.data[0]'
```

### Per-campaign, last 30 days

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/insights?fields=campaign_name,campaign_id,impressions,clicks,spend,ctr,cpc,actions,purchase_roas&level=campaign&date_preset=last_30d&access_token=$META_ADS_TOKEN" | jq '.data[] | {campaign_name, impressions, clicks, spend, ctr, cpc}'
```

### Explicit date range

```bash
curl -s -G "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/insights" \
  --data-urlencode 'fields=impressions,clicks,spend,ctr,cpc,reach,actions' \
  --data-urlencode 'time_range={"since":"2026-01-01","until":"2026-01-31"}' \
  --data-urlencode "access_token=$META_ADS_TOKEN" | jq '.data[0]'
```

Use `-G` + `--data-urlencode` for `time_range` — it contains braces and quotes that break in a single-string URL.

### Daily breakdown

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/insights?fields=impressions,clicks,spend,ctr&date_preset=last_7d&time_increment=1&access_token=$META_ADS_TOKEN" | jq '.data[] | {date_start, impressions, clicks, spend}'
```

### Breakdown by age + gender

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/insights?fields=impressions,clicks,spend&date_preset=last_30d&breakdowns=age,gender&access_token=$META_ADS_TOKEN" | jq '.data[] | {age, gender, impressions, clicks, spend}'
```

### Breakdown by placement / device

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/insights?fields=impressions,clicks,spend&date_preset=last_30d&breakdowns=publisher_platform,platform_position,device_platform&access_token=$META_ADS_TOKEN" | jq '.data[]'
```

## Custom audiences

```bash
curl -s "https://graph.facebook.com/v22.0/$META_ADS_ACCOUNT_ID/customaudiences?fields=id,name,approximate_count_lower_bound,approximate_count_upper_bound&access_token=$META_ADS_TOKEN" | jq '.data[] | {id, name, size: .approximate_count_lower_bound}'
```

## Gotchas

- **Money is in cents.** `daily_budget: 1000` = $10.00 USD. `spend: "42.73"` is already in major units (dollars) — yes, Meta is inconsistent. Budgets = cents, insights spend = major.
- **`date_preset` values:** `today`, `yesterday`, `last_7d`, `last_14d`, `last_28d`, `last_30d`, `last_90d`, `this_month`, `last_month`, `this_quarter`, `last_quarter`, `this_year`, `last_year`, `maximum`.
- **Pagination:** responses with `paging.next` have more data. Fetch that URL for the next page.
- **Rate limits:** error codes `17`, `32`, or `613` mean slow down. Wait and retry once, then report back to the user instead of looping.
- **Auth errors:** code `190` = token expired or revoked. Regenerate (see Setup) — don't retry.
- **Action types:** `actions` is an array of `{action_type, value}`. For purchases look for `omni_purchase` or `purchase`; for leads `lead` or `onsite_conversion.lead_grouped`. Which one depends on the pixel/CAPI setup — show the raw array if unsure.

## Setup (one-time, user-side)

If `$META_ADS_TOKEN` is missing or expired:

1. Go to [Meta Business Manager](https://business.facebook.com) → **Business Settings** → **Users** → **System Users** → add one (or pick existing). Assign it to your ad account with **View performance** permission.
2. In your Meta developer app → **System User** panel → **Generate New Token** → pick `ads_read` scope → pick **Never** expiry. System User tokens are long-lived and don't need refresh.
3. On the host (not inside the container), add to `/Users/avishay/fishbone/nanoclaw/.env`:
   ```
   META_ADS_TOKEN=EAA...
   META_ADS_ACCOUNT_ID=act_1234567890
   ```
4. Restart NanoClaw so the new env passthrough takes effect:
   ```
   launchctl kickstart -k gui/$(id -u)/com.nanoclaw
   ```
5. Run the smoke test above to confirm.

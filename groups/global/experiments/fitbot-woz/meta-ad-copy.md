# Meta Ads Copy — Fitbot Smoke Test (2026-04-21)

Copy-paste fields for the 3 review ads in Meta Ads Manager.
**Campaign:** `Fitbot Smoke Test · Reviews · 2026-04-21`
**Ad set:** `Reviews · Advantage+ IL 22-40`

## Fields identical across all 3 ads

| Field | Value |
|---|---|
| Page identity | פיט בוט |
| Format | Single image |
| Headline | `מאמן אישי AI בוואטסאפ` |
| Description | `חינם · ללא כרטיס אשראי` |
| Display link | `fitbot.getfishbone.ai` |
| Call to action | Learn More (`למד עוד`) |

## Ad 1 — Review · Noa · weight loss + family

**Media:** `[Noa review image]`

**Primary text:**

```
מה אומרים עלינו? ביקורות 1 כוכב בלבד.
```

**Website URL:**

```
https://fitbot.getfishbone.ai?utm_source=meta&utm_medium=paid&utm_campaign=fitbot_smoketest&utm_content=review_noa
```

## Ad 2 — Review · Nehorai · muscle gain + closet

**Media:** `[Nehorai review image]`

**Primary text:**

```
הלקוחות מתלוננים. אנחנו חייבים להודות שהם צודקים.
```

**Website URL:**

```
https://fitbot.getfishbone.ai?utm_source=meta&utm_medium=paid&utm_campaign=fitbot_smoketest&utm_content=review_nehorai
```

## Ad 3 — Review · Dana · ate everything

**Media:** `[Dana review image]`

**Primary text:**

```
שלוש ביקורות אמיתיות. כולן של כוכב אחד. תהיו בשקט.
```

**Website URL:**

```
https://fitbot.getfishbone.ai?utm_source=meta&utm_medium=paid&utm_campaign=fitbot_smoketest&utm_content=review_dana
```

## Notes

- Primary texts deliberately differ per ad to reduce Andromeda engine similarity clustering (Oct 2025 creative-diversity suppression risk flagged by /ads-meta audit).
- Hebrew voice on the 3 primary texts is my first draft — rewrite mercilessly if they read stiff.
- UTM content tag differs per ad so you can attribute which review drove which signup in Formspree / Google Sheet after the campaign ends.
- Campaign-level settings: Leads objective, CBO, ₪100/day × 7 days, Advantage+ audience + placements, Conversion event = Lead, Pixel 921413210895604.

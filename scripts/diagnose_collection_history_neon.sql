-- F176-T01 — Read-only diagnosis of collection price history (Neon / PostgreSQL)
--
-- READ-ONLY: only SELECT statements, wrapped in a READ ONLY transaction that
-- is rolled back at the end. Safe to run against production.
--
-- How to run (from a machine with DATABASE_URL in .env):
--   psql "$DATABASE_URL" -f scripts/diagnose_collection_history_neon.sql > f176_neon.txt
-- or paste block by block into the Neon SQL editor (skip BEGIN/ROLLBACK there).
--
-- Before running Q2/Q5, edit the card id list in the `ids` CTE (search "EDIT").
-- Tip: pick ids from Q6 (collection entries) or from /collection/:id in the UI.

BEGIN TRANSACTION READ ONLY;

-- Q1 — external_id families in price_observations (H1, H4, H6 volume)
SELECT
    CASE
        WHEN external_id LIKE 'liga\_catalog\_%' ESCAPE '\' THEN 'liga_catalog_%'
        WHEN external_id ~ '^liga_[0-9]+_foil$'              THEN 'liga_%_foil'
        WHEN external_id ~ '^liga_[0-9]+$'                   THEN 'liga_%'
        WHEN external_id ~ '^manual_[0-9]+$'                 THEN 'manual_%'
        ELSE 'other (myp/source_cards)'
    END                                  AS family,
    source,
    COUNT(*)                             AS rows,
    COUNT(DISTINCT external_id)          AS series,
    MIN(observed_at)                     AS first_day,
    MAX(observed_at)                     AS last_day
FROM price_observations
GROUP BY 1, 2
ORDER BY 1, 2;

-- Q2 — points per day per card, for a given list of card ids (H3, H4, H5)
-- Maps every observation back to a card id: direct keys (liga_{id},
-- liga_{id}_foil, manual_{id}) by regex, everything else via source_cards.
WITH ids(card_id) AS (
    VALUES (1), (2), (3)            -- EDIT: card ids to inspect
),
direct AS (
    SELECT po.*,
           CAST(substring(po.external_id FROM '^(?:liga|manual)_([0-9]+)(?:_foil)?$') AS INTEGER)
               AS card_id,
           'direct' AS via
    FROM price_observations po
    WHERE po.external_id ~ '^(liga|manual)_[0-9]+(_foil)?$'
),
linked AS (
    SELECT po.*, sc.card_id, 'source_cards' AS via
    FROM price_observations po
    JOIN source_cards sc ON sc.external_id = po.external_id
),
all_obs AS (
    SELECT * FROM direct
    UNION ALL
    SELECT * FROM linked
)
SELECT
    a.card_id,
    a.observed_at,
    COUNT(*)                                                     AS points,
    STRING_AGG(a.source || ':' || a.external_id, ', ' ORDER BY a.source, a.external_id)
                                                                 AS series,
    BOOL_OR(a.external_id LIKE '%\_foil' ESCAPE '\')             AS has_foil,
    BOOL_OR(a.external_id NOT LIKE '%\_foil' ESCAPE '\')         AS has_normal
FROM all_obs a
JOIN ids ON ids.card_id = a.card_id
WHERE a.observed_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY a.card_id, a.observed_at
ORDER BY a.card_id, a.observed_at;

-- Q3 — daily_snapshot freshness and fabricated backfill (H3, H6)
-- run_daily_snapshot always writes observed_at = today; rows dated before
-- their insertion day come from backfill_snapshots (current price copied back).
SELECT
    MAX(observed_at)                                                  AS last_snapshot_day,
    COUNT(DISTINCT observed_at) FILTER (WHERE observed_at >= CURRENT_DATE - 30)
                                                                      AS snapshot_days_last_30,
    COUNT(*)                                                          AS snapshot_rows,
    COUNT(*) FILTER (WHERE observed_at < CAST(created_at AS DATE))    AS backfilled_rows,
    COUNT(DISTINCT external_id)                                       AS snapshot_series
FROM price_observations
WHERE source = 'daily_snapshot';

-- Q4 — real (non-snapshot) Liga observation cadence per card, last 90 days (H3)
SELECT
    width_bucket(real_days, 0, 91, 7)    AS bucket,
    MIN(real_days)                       AS min_days,
    MAX(real_days)                       AS max_days,
    COUNT(*)                             AS series
FROM (
    SELECT external_id, COUNT(DISTINCT observed_at) AS real_days
    FROM price_observations
    WHERE source = 'liga'
      AND external_id ~ '^liga_[0-9]+(_foil)?$'
      AND observed_at >= CURRENT_DATE - 90
    GROUP BY external_id
) t
GROUP BY 1
ORDER BY 1;

-- Q5 — current endpoint vs. available, per collection entry (H1, H2)
-- "endpoint" replicates GET /collection/{id}/history today:
--   source_cards of card_id x source IN (sc.source, 'jsonld_snapshot'), last 30 days.
-- "available" = every observation under source_cards + liga_{id}[_foil] + manual_{id}.
WITH ids(card_id) AS (
    VALUES (1), (2), (3)            -- EDIT: same list as Q2 (or remove the JOIN to scan all)
),
entries AS (
    SELECT uc.id AS entry_id, uc.card_id, uc.extras,
           (LOWER(COALESCE(uc.extras, '')) LIKE '%foil%') AS is_foil
    FROM user_collection uc
    JOIN ids ON ids.card_id = uc.card_id
),
endpoint AS (
    SELECT e.entry_id, COUNT(po.id) AS endpoint_points
    FROM entries e
    LEFT JOIN source_cards sc ON sc.card_id = e.card_id
    LEFT JOIN price_observations po
           ON po.external_id = sc.external_id
          AND po.source IN (sc.source, 'jsonld_snapshot')
          AND po.observed_at >= CURRENT_DATE - 30
    GROUP BY e.entry_id
),
available AS (
    SELECT e.entry_id,
           COUNT(po.id)                                                AS available_points,
           COUNT(po.id) FILTER (WHERE po.source = 'daily_snapshot')    AS snapshot_points,
           COUNT(po.id) FILTER (WHERE po.external_id = 'liga_' || e.card_id)          AS liga_normal,
           COUNT(po.id) FILTER (WHERE po.external_id = 'liga_' || e.card_id || '_foil') AS liga_foil
    FROM entries e
    LEFT JOIN price_observations po
           ON po.observed_at >= CURRENT_DATE - 30
          AND (po.external_id IN ('liga_' || e.card_id,
                                  'liga_' || e.card_id || '_foil',
                                  'manual_' || e.card_id)
               OR po.external_id IN (SELECT sc.external_id FROM source_cards sc
                                     WHERE sc.card_id = e.card_id))
    GROUP BY e.entry_id
)
SELECT e.entry_id, e.card_id, e.is_foil, ep.endpoint_points, av.available_points,
       av.available_points - ep.endpoint_points AS lost_points,
       av.snapshot_points, av.liga_normal, av.liga_foil
FROM entries e
JOIN endpoint ep USING (entry_id)
JOIN available av USING (entry_id)
ORDER BY e.entry_id;

-- Q6 — collection-wide coverage (H1 at scale, H4 foil)
SELECT
    COUNT(*)                                                           AS entries,
    COUNT(*) FILTER (WHERE uc.card_id IS NULL)                         AS unlinked,
    COUNT(*) FILTER (WHERE uc.card_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM source_cards sc WHERE sc.card_id = uc.card_id))  AS no_source_cards,
    COUNT(*) FILTER (WHERE EXISTS (
        SELECT 1 FROM price_observations po
        WHERE po.external_id IN ('liga_' || uc.card_id, 'liga_' || uc.card_id || '_foil')))
                                                                       AS with_direct_liga,
    COUNT(*) FILTER (WHERE LOWER(COALESCE(uc.extras, '')) LIKE '%foil%') AS foil_entries,
    COUNT(*) FILTER (WHERE LOWER(COALESCE(uc.extras, '')) LIKE '%foil%' AND EXISTS (
        SELECT 1 FROM price_observations po
        WHERE po.external_id = 'liga_' || uc.card_id || '_foil'))      AS foil_with_liga_foil
FROM user_collection uc;

ROLLBACK;

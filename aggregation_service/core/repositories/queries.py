from sqlalchemy import text

query_for_find_pairs = text(
        """
        WITH ann_candidates AS (
            SELECT
                a.id                     AS a_id,
                a.platform               AS a_platform,
                a.platform_market_id     AS a_market_id,
                a.title                  AS a_title,
                a.normalized_title       AS a_normalized_title,
                a.semantic_text          AS a_semantic_text,
                a.description            AS a_description,
                a.embedding              AS a_embedding,
                a.semantic_embedding     AS a_semantic_embedding,
                a.close_time             AS a_close_time,
                a.outcomes               AS a_outcomes,

                b.id                     AS b_id,
                b.platform               AS b_platform,
                b.platform_market_id     AS b_market_id,
                b.title                  AS b_title,
                b.normalized_title       AS b_normalized_title,
                b.semantic_text          AS b_semantic_text,
                b.description            AS b_description,
                b.embedding              AS b_embedding,
                b.semantic_embedding     AS b_semantic_embedding,
                b.close_time             AS b_close_time,
                b.outcomes               AS b_outcomes,

                (a.embedding <-> b.embedding) AS min_distance
            FROM markets a
                     JOIN LATERAL (
                SELECT
                    id,
                    platform,
                    platform_market_id,
                    title,
                    normalized_title,
                    semantic_text,
                    description,
                    embedding,
                    semantic_embedding,
                    close_time,
                    outcomes
                FROM markets b
                WHERE b.platform <> a.platform
                  AND b.embedding IS NOT NULL
                ORDER BY b.embedding <-> a.embedding
                    LIMIT :pair_limit
            ) b ON true
        WHERE a.embedding IS NOT NULL
            )

        SELECT
            a_id,
            a_platform,
            a_market_id,
            a_title,
            a_normalized_title,
            a_semantic_text,
            a_description,
            a_embedding,
            a_semantic_embedding,
            a_close_time,
            a_outcomes,

            b_id,
            b_platform,
            b_market_id,
            b_title,
            b_normalized_title,
            b_semantic_text,
            b_description,
            b_embedding,
            b_semantic_embedding,
            b_close_time,
            b_outcomes,
            min_distance
        FROM ann_candidates
        WHERE min_distance <= :max_distance
          AND a_id < b_id
          AND NOT EXISTS (
            SELECT 1
            FROM pairs p
            WHERE jsonb_array_length(p.market_ids) = 2
              AND (
                (p.market_ids->>0 = a_market_id AND p.market_ids->>1 = b_market_id)
                    OR (p.market_ids->>0 = b_market_id AND p.market_ids->>1 = a_market_id)
                )
        )
          AND NOT EXISTS (
            SELECT 1
            FROM invalid_pair ip
            WHERE (ip.a_market_id = ann_candidates.a_market_id AND ip.b_market_id = ann_candidates.b_market_id)
               OR (ip.a_market_id = ann_candidates.b_market_id AND ip.b_market_id = ann_candidates.a_market_id)
        )
        ORDER BY min_distance ASC
            LIMIT :limit
        OFFSET :offset;
        """
    )


query_for_cleanup_top_n = text(
            """
            DELETE FROM pairs p
            USING (
                SELECT pair_id
                FROM (
                    SELECT pair_id,
                           ROW_NUMBER() OVER (
                               PARTITION BY a_market_id
                               ORDER BY final_score DESC
                           ) rn
                    FROM pair_a_index
                ) ranked
                WHERE rn > :top_n
            ) excess
            WHERE p.id = excess.pair_id
            """
        )

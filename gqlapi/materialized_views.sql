CREATE MATERIALIZED VIEW orden_details_status_view as (
        WITH last_orden_status AS (
            WITH rcos AS (
                SELECT
                    orden_id,
                    status,
                    ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
                FROM orden_status
        )
            SELECT * FROM rcos WHERE row_num = 1
        ),
        last_orden_version AS (
            WITH last_upd AS (
                SELECT
                    orden_id,
                    id as orden_details_id,
                    ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
                FROM orden_details
            )
            SELECT orden_details_id, orden_id FROM last_upd WHERE row_num = 1
        )
        SELECT
            orden_details.*,
            los.status
        FROM last_orden_version lov
        JOIN orden_details ON orden_details.id = lov.orden_details_id
        JOIN last_orden_status los ON los.orden_id = lov.orden_id
);

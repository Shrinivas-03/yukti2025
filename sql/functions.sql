-- Function to get detailed event statistics
CREATE OR REPLACE FUNCTION get_event_statistics()
RETURNS TABLE (
    event_id UUID,
    event_name TEXT,
    category_name TEXT,
    event_type TEXT,
    team_size INTEGER,
    cost NUMERIC,
    total_registrations BIGINT,
    paid_registrations BIGINT,
    pending_registrations BIGINT,
    individual_count BIGINT,
    team_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH event_stats AS (
        SELECT 
            e.id,
            COUNT(DISTINCT er.registration_id) as total_reg,
            COUNT(DISTINCT CASE WHEN r.payment_status = 'paid' THEN er.registration_id END) as paid_reg,
            COUNT(DISTINCT CASE WHEN r.payment_status != 'paid' OR r.payment_status IS NULL THEN er.registration_id END) as pending_reg,
            COUNT(DISTINCT CASE WHEN e.type = 'individual' THEN er.registration_id END) as ind_count,
            COUNT(DISTINCT CASE WHEN e.type = 'team' THEN er.registration_id END) as team_count
        FROM events e
        LEFT JOIN event_registrations er ON e.id = er.event_id
        LEFT JOIN registrations r ON er.registration_id = r.id
        GROUP BY e.id
    )
    SELECT 
        e.id AS event_id,
        e.name AS event_name,
        c.name AS category_name,
        e.type AS event_type,
        e.team_size,
        e.cost,
        COALESCE(es.total_reg, 0) AS total_registrations,
        COALESCE(es.paid_reg, 0) AS paid_registrations,
        COALESCE(es.pending_reg, 0) AS pending_registrations,
        COALESCE(es.ind_count, 0) AS individual_count,
        COALESCE(es.team_count, 0) AS team_count
    FROM events e
    LEFT JOIN event_stats es ON e.id = es.id
    LEFT JOIN categories c ON e.category_id = c.id
    ORDER BY c.name, e.name;
END;
$$ LANGUAGE plpgsql;

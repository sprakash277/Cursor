-- TPC-DI Query 1: Simple aggregation on Daily Market
-- This query aggregates daily market data by security

SELECT 
    dm.SK_SecurityID,
    s.Symbol,
    s.Name,
    COUNT(*) as trading_days,
    AVG(dm.ClosePrice) as avg_close_price,
    MAX(dm.DayHigh) as max_high,
    MIN(dm.DayLow) as min_low,
    SUM(dm.Volume) as total_volume
FROM ${catalog}.${schema}.FactDailyMarket dm
JOIN ${catalog}.${schema}.DimSecurity s 
    ON dm.SK_SecurityID = s.SK_SecurityID
WHERE dm.SK_DateID BETWEEN 1 AND 365  -- First year
GROUP BY dm.SK_SecurityID, s.Symbol, s.Name
ORDER BY total_volume DESC
LIMIT 100;

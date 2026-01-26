-- TPC-DI Query 2: Customer trade analysis
-- This query analyzes customer trading patterns

SELECT 
    c.SK_CustomerID,
    c.CustomerID,
    c.FirstName,
    c.LastName,
    COUNT(DISTINCT t.TradeID) as num_trades,
    SUM(t.Quantity) as total_quantity,
    AVG(t.BidPrice) as avg_bid_price,
    AVG(t.AskPrice) as avg_ask_price,
    SUM(CASE WHEN t.TradeType = 'Buy' THEN t.Quantity ELSE 0 END) as buy_quantity,
    SUM(CASE WHEN t.TradeType = 'Sell' THEN t.Quantity ELSE 0 END) as sell_quantity
FROM ${catalog}.${schema}.FactTrade t
JOIN ${catalog}.${schema}.DimCustomer c 
    ON t.SK_CustomerID = c.SK_CustomerID
WHERE t.SK_DateID BETWEEN 1 AND 365  -- First year
GROUP BY c.SK_CustomerID, c.CustomerID, c.FirstName, c.LastName
HAVING COUNT(DISTINCT t.TradeID) > 10
ORDER BY total_quantity DESC
LIMIT 100;

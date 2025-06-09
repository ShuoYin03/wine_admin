SELECT
    a.external_id,
    a.url,
    COUNT(l.id) AS lot_count
FROM
    wine_admin.auctions a
LEFT JOIN
    wine_admin.lots l ON a.external_id = l.auction_id
WHERE
    a.auction_house = 'Sotheby''s'
GROUP BY
    a.external_id, a.url
ORDER BY
    lot_count DESC;

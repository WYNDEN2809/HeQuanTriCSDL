/* =====================================================================
   Du lieu danh muc 
   Brand, User, BrandMember, Location, Perfume, Machine, MachineSlot
   Chay sau file 01.
   ===================================================================== */
USE ScentStationDB;
GO
IF EXISTS (SELECT 1 FROM Brand)
BEGIN
    RAISERROR('Du lieu danh muc da ton tai. Chay lai file 01 neu muon lam moi tu dau.', 16, 1);
    RETURN;
END
SET NOCOUNT ON;

/* ---------- 2.1 Brand ---------- */
INSERT Brand(name, description, logo_url, is_active) VALUES
 ('Lumiere Parfums',  'Thuong hieu nuoc hoa Phap huong hoa co dien',        'https://cdn.scentstation.vn/logos/lumiere.png', 1),
 ('Aurelia Fragrance','Nuoc hoa cao cap huong go va ho phach',              'https://cdn.scentstation.vn/logos/aurelia.png', 1),
 ('Saigon Scents',    'Nuoc hoa noi dia lay cam hung tu van hoa Sai Gon',   'https://cdn.scentstation.vn/logos/saigon.png',  1),
 ('Noir & Co',        'Dong nuoc hoa niche, huong dam va quyen ru',         'https://cdn.scentstation.vn/logos/noir.png',    1),
 ('Hoa Lan Perfume',  'Nuoc hoa thien nhien huong hoa lan va tra xanh',     'https://cdn.scentstation.vn/logos/hoalan.png',  1);

CREATE TABLE #BrandSlug (BrandID int PRIMARY KEY, slug varchar(20));
INSERT #BrandSlug
SELECT BrandID, CASE name WHEN 'Lumiere Parfums' THEN 'lumiere' WHEN 'Aurelia Fragrance' THEN 'aurelia'
                          WHEN 'Saigon Scents' THEN 'saigon' WHEN 'Noir & Co' THEN 'noir' ELSE 'hoalan' END
FROM Brand;

/* ---------- 2.2 User + BrandMember ---------- */
INSERT [User](username, email, password_hash, role, is_active)
VALUES ('superadmin', 'superadmin@scentstation.vn',
        CONVERT(varchar(64), HASHBYTES('SHA2_256', 'P@ssw0rd!superadmin'), 2), 'SUPER_ADMIN', 1);

DECLARE @roles TABLE (uname varchar(20), brand_role varchar(20));
INSERT @roles VALUES ('admin','BRAND_ADMIN'),('ops','OPS_MANAGER'),('tech1','TECHNICIAN'),
                     ('tech2','TECHNICIAN'),('inv','INVENTORY_STAFF'),('viewer','VIEWER');

INSERT [User](username, email, password_hash, role, is_active)
SELECT r.uname + '_' + b.slug,
       r.uname + '_' + b.slug + '@scentstation.vn',
       CONVERT(varchar(64), HASHBYTES('SHA2_256', 'P@ssw0rd!' + r.uname + '_' + b.slug), 2),
       'USER',
       CASE WHEN b.slug = 'hoalan' AND r.uname = 'viewer' THEN 0 ELSE 1 END
FROM #BrandSlug b CROSS JOIN @roles r;

INSERT BrandMember(UserID, BrandID, brand_role)
SELECT u.UserID, b.BrandID, r.brand_role
FROM #BrandSlug b CROSS JOIN @roles r
JOIN [User] u ON u.username = r.uname + '_' + b.slug;

/* ---------- 2.3 Location (3 điểm / brand) ---------- */
INSERT Location(BrandID, name, address, is_active, description)
SELECT b.BrandID, l.nm + ' - ' + br.name, l.addr, 1, 'Khu kiosk trai nghiem tai ' + l.nm
FROM #BrandSlug b
JOIN Brand br ON br.BrandID = b.BrandID
CROSS JOIN (VALUES
    ('Vincom Dong Khoi',  '72 Le Thanh Ton, Quan 1, TP.HCM'),
    ('Royal City',        '72A Nguyen Trai, Thanh Xuan, Ha Noi'),
    ('Vincom Da Nang',    '910A Ngo Quyen, Son Tra, Da Nang')
) l(nm, addr);

/* ---------- 2.4 Perfume (8 mùi / brand) ---------- */
INSERT Perfume(BrandID, name, description, is_active, price_per_spray)
SELECT b.BrandID, p.nm,
       'Notes: ' + p.notes + '. Thuoc ' + br.name,
       CASE WHEN p.n = 8 AND b.BrandID = 3 THEN 0 ELSE 1 END,
       CAST(10000 + p.n * 5000 + (b.BrandID % 3) * 2000 AS decimal(10,2))
FROM #BrandSlug b
JOIN Brand br ON br.BrandID = b.BrandID
CROSS JOIN (VALUES
    (1,'Midnight Rose',  'Rose, Patchouli, Vanilla'),
    (2,'Citrus Dawn',    'Bergamot, Lemon, Neroli'),
    (3,'Ocean Mist',     'Sea Salt, Marine, Cedar'),
    (4,'Velvet Oud',     'Oud, Amber, Leather'),
    (5,'Jasmine Tea',    'Jasmine, Green Tea, Musk'),
    (6,'Amber Nights',   'Amber, Tonka, Cinnamon'),
    (7,'White Musk',     'White Musk, Lily, Sandalwood'),
    (8,'Green Vetiver',  'Vetiver, Basil, Grapefruit')
) p(n, nm, notes);

/* ---------- 2.5 Machine (2 máy / location = 30 máy) ---------- */
INSERT Machine(BrandID, LocationID, name, status, serial_number, last_seen_at)
SELECT x.BrandID, x.LocationID,
       'Kiosk-' + RIGHT('000' + CAST(x.mn + 1 AS varchar(3)), 3),
       x.st,
       'SS-2026-' + RIGHT('00000' + CAST(x.mn + 1 AS varchar(5)), 5),
       CASE x.st WHEN 'ONLINE'  THEN DATEADD(SECOND, -CAST(x.mn * 7 % 50 AS int), SYSDATETIME())
                 WHEN 'OFFLINE' THEN DATEADD(HOUR,   -CAST(6 + x.mn AS int),      SYSDATETIME())
                 ELSE                DATEADD(MINUTE, -CAST(10 + x.mn AS int),     SYSDATETIME()) END
FROM (
    SELECT L.BrandID, L.LocationID, CAST(L.ln * 2 + kk.n AS int) AS mn,
           CASE CAST(L.ln * 2 + kk.n AS int) % 10
                WHEN 3 THEN 'OFFLINE' WHEN 6 THEN 'MAINTENANCE' WHEN 9 THEN 'DISABLED'
                WHEN 7 THEN 'ERROR'   ELSE 'ONLINE' END AS st
    FROM (SELECT LocationID, BrandID, ROW_NUMBER() OVER (ORDER BY LocationID) - 1 AS ln FROM Location) L
    CROSS JOIN (VALUES (0),(1)) kk(n)
) x;

/* ---------- 2.6 MachineSlot (4 slot / máy = 120 slot) ---------- */
;WITH P AS (
    SELECT PerfumeID, BrandID, price_per_spray,
           ROW_NUMBER() OVER (PARTITION BY BrandID ORDER BY PerfumeID) - 1 AS pn
    FROM Perfume
), M AS (
    SELECT MachineID, BrandID, ROW_NUMBER() OVER (ORDER BY MachineID) - 1 AS mn FROM Machine
), S AS (
    SELECT 0 AS s UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
)
INSERT MachineSlot(PerfumeID, MachineID, slot_number, quantity, price_per_spray,
                   low_stock_threshold, spray_duration, capacity, status)
SELECT p.PerfumeID, m.MachineID, s.s + 1,
       400 + ABS(CHECKSUM(NEWID())) % 600,
       p.price_per_spray, 50, 300 + (s.s * 100), 1000, 'ACTIVE'
FROM M m CROSS JOIN S s
JOIN P p ON p.BrandID = m.BrandID AND p.pn = (m.mn * 4 + s.s) % 8;

DROP TABLE #BrandSlug;

SELECT 'User' AS TableName, COUNT(*) AS Total FROM [User]
UNION ALL SELECT 'Brand', COUNT(*) FROM Brand
UNION ALL SELECT 'BrandMember', COUNT(*) FROM BrandMember
UNION ALL SELECT 'Location', COUNT(*) FROM Location
UNION ALL SELECT 'Perfume', COUNT(*) FROM Perfume
UNION ALL SELECT 'Machine', COUNT(*) FROM Machine
UNION ALL SELECT 'MachineSlot', COUNT(*) FROM MachineSlot;
GO

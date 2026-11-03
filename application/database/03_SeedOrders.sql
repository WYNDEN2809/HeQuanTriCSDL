/* =====================================================================
   Giao dich ban hang
   Orders, Payment, DispenseTransaction, InventoryLog
   Chay sau file 02. Chinh @TotalOrders de tang/giam thoi gian chay.
   ===================================================================== */
USE ScentStationDB;
GO
IF NOT EXISTS (SELECT 1 FROM MachineSlot)
BEGIN
    RAISERROR('Chua co du lieu danh muc. Hay chay file 02 truoc.', 16, 1);
    RETURN;
END
IF EXISTS (SELECT 1 FROM Orders)
BEGIN
    RAISERROR('Orders da co du lieu. Chay lai file 01 + 02 neu muon lam moi.', 16, 1);
    RETURN;
END
SET NOCOUNT ON;
DECLARE @t0 datetime2 = SYSDATETIME();
DECLARE @TotalOrders int = 30000;   -- so don hang (moi don keo theo payment, dispense, inventory log)

SELECT ROW_NUMBER() OVER (ORDER BY s.MachineSlotID) AS rn, s.MachineSlotID, s.PerfumeID,
       s.MachineID, s.price_per_spray, s.capacity, m.BrandID
INTO #S FROM MachineSlot s JOIN Machine m ON m.MachineID = s.MachineID;
DECLARE @slotCount int = (SELECT COUNT(*) FROM #S);

SELECT BrandID, MIN(UserID) AS UserID INTO #Inv FROM BrandMember
WHERE brand_role = 'INVENTORY_STAFF' GROUP BY BrandID;

/* ---------- 3.1 Orders + Payment + DispenseTransaction + InventoryLog ---------- */
DECLARE @i int = 0, @r int, @k int, @k2 int, @s1 int, @s2 int;
DECLARE @sid int, @pid int, @mid int, @brand int, @cap int, @oid int, @qb int, @inv int, @adj int;
DECLARE @price decimal(10,2);
DECLARE @created datetime2, @paid datetime2, @start datetime2 = DATEADD(DAY, -90, SYSDATETIME());
DECLARE @roll int, @ost varchar(20), @pst varchar(20), @dst varchar(20), @hasPay bit, @hasDisp bit;
DECLARE @err varchar(500);

WHILE @i < @TotalOrders
BEGIN
    SET @i += 1;
    SET @r = 1 + ABS(CHECKSUM(NEWID())) % @slotCount;
    SELECT @sid = MachineSlotID, @pid = PerfumeID, @mid = MachineID, @brand = BrandID,
           @price = price_per_spray, @cap = capacity
    FROM #S WHERE rn = @r;

    -- thời gian tăng dần theo thứ tự đơn trong 90 ngày gần nhất
    SET @created = DATEADD(SECOND, CAST(CAST(@i AS bigint) * 7776000 / @TotalOrders AS int), @start);
    SET @roll = ABS(CHECKSUM(NEWID())) % 100;

    IF @roll < 80
    BEGIN
        SELECT @ost = 'DISPENSED', @pst = 'SUCCESS', @dst = 'SUCCESS', @hasPay = 1, @hasDisp = 1
    END
    ELSE IF @roll < 83
    BEGIN
        SELECT @ost = 'DISPENSE_FAILED', @pst = 'SUCCESS', @dst = 'FAILED', @hasPay = 1, @hasDisp = 1
    END
    ELSE IF @roll < 85
    BEGIN
        SELECT @ost = 'REFUNDED', @pst = 'REFUNDED', @dst = 'FAILED', @hasPay = 1, @hasDisp = 1
    END
    ELSE IF @roll < 87
    BEGIN
        SELECT @ost = 'REVIEW', @pst = 'SUCCESS', @dst = 'UNCERTAIN', @hasPay = 1, @hasDisp = 1
    END
    ELSE IF @roll < 93
    BEGIN
        SELECT @ost = 'EXPIRED', @pst = NULL, @dst = NULL, @hasPay = 0, @hasDisp = 0
    END
    ELSE IF @roll < 97
    BEGIN
        SELECT @ost = 'CANCELLED', @pst = 'CANCELLED', @dst = NULL, @hasPay = 1, @hasDisp = 0
    END
    ELSE
    BEGIN
        SELECT @ost = 'FAILED', @pst = 'FAILED', @dst = NULL, @hasPay = 1, @hasDisp = 0
    END

    INSERT Orders(MachineSlotID, PerfumeID, unit_price, quantity, amount, payment_reference,
                  currency, status, expires_at, created_at)
    VALUES (@sid, @pid, @price, 1, @price,
            'PAY-' + CONVERT(char(8), @created, 112) + '-' + RIGHT('000000' + CAST(@i AS varchar(10)), 6),
            'VND', @ost, DATEADD(MINUTE, 5, @created), @created);
    SET @oid = SCOPE_IDENTITY();

    SET @paid = DATEADD(SECOND, 5 + ABS(CHECKSUM(NEWID())) % 55, @created);

    IF @hasPay = 1
    BEGIN
        SET @k = 1 + ABS(CHECKSUM(NEWID())) % 4;
        INSERT Payment(OrderID, method, provider_transaction_id, amount, status, paid_at, created_at)
        VALUES (@oid, CHOOSE(@k, 'VIETQR', 'MOMO', 'ZALOPAY', 'VNPAY'),
                'TXN' + REPLACE(CAST(NEWID() AS varchar(36)), '-', ''),
                @price, @pst,
                CASE WHEN @pst IN ('SUCCESS', 'REFUNDED') THEN @paid END,
                @created);
    END

    IF @hasDisp = 1
    BEGIN
        SET @k2 = 1 + ABS(CHECKSUM(NEWID())) % 4;
        SET @s1 = 1 + ABS(CHECKSUM(NEWID())) % 3;
        SET @s2 = 4 + ABS(CHECKSUM(NEWID())) % 5;
        SET @err = CASE WHEN @dst = 'SUCCESS'   THEN NULL
                        WHEN @dst = 'UNCERTAIN' THEN 'No device result received before timeout'
                        ELSE CHOOSE(@k2, 'Door is open', 'Slot is empty', 'Actuator timeout', 'Sensor error') END;
        INSERT DispenseTransaction(OrderID, status, command_id, error_message, expires_at,
                                   acknowledged_at, executed_at, created_at)
        VALUES (@oid, @dst, 'CMD-' + REPLACE(CAST(NEWID() AS varchar(36)), '-', ''), @err,
                DATEADD(MINUTE, 2, @paid),
                CASE WHEN @dst IN ('SUCCESS', 'FAILED') THEN DATEADD(SECOND, @s1, @paid) END,
                CASE WHEN @dst = 'SUCCESS' THEN DATEADD(SECOND, @s2, @paid) END,
                DATEADD(SECOND, 1, @paid));
    END

    IF @ost = 'DISPENSED'
    BEGIN
        SELECT @qb = quantity FROM MachineSlot WHERE MachineSlotID = @sid;

        IF @qb <= 30   -- sắp hết => nhân viên kho refill
        BEGIN
            SELECT @inv = UserID FROM #Inv WHERE BrandID = @brand;
            INSERT InventoryLog(UserID, MachineSlotID, OrderID, change_type, quantity_before,
                                quantity_after, change_amount, reason, created_at)
            VALUES (@inv, @sid, NULL, 'REFILL', @qb, @cap, @cap - @qb, 'Scheduled refill', DATEADD(SECOND, -30, @paid));
            SET @qb = @cap;
        END

        INSERT InventoryLog(UserID, MachineSlotID, OrderID, change_type, quantity_before,
                            quantity_after, change_amount, reason, created_at)
        VALUES (NULL, @sid, @oid, 'SALE', @qb, @qb - 1, -1, 'Customer spray', DATEADD(SECOND, 6, @paid));
        SET @qb = @qb - 1;
        UPDATE MachineSlot SET quantity = @qb WHERE MachineSlotID = @sid;

        IF ABS(CHECKSUM(NEWID())) % 200 = 0   -- thỉnh thoảng có điều chỉnh tồn kho sau đối soát cảm biến
        BEGIN
            SET @adj = 1 + ABS(CHECKSUM(NEWID())) % 3;
            SELECT @inv = UserID FROM #Inv WHERE BrandID = @brand;
            INSERT InventoryLog(UserID, MachineSlotID, OrderID, change_type, quantity_before,
                                quantity_after, change_amount, reason, created_at)
            VALUES (@inv, @sid, NULL, 'ADJUSTMENT', @qb, @qb - @adj, -@adj, 'Sensor reconciliation', DATEADD(SECOND, 60, @paid));
            UPDATE MachineSlot SET quantity = @qb - @adj WHERE MachineSlotID = @sid;
        END
    END

    IF @i % 5000 = 0
        RAISERROR('>> Orders: %d / %d', 0, 1, @i, @TotalOrders) WITH NOWAIT;
END

-- cập nhật trạng thái slot theo tồn kho cuối cùng
UPDATE MachineSlot
SET status = CASE WHEN quantity <= 0 THEN 'EMPTY'
                  WHEN quantity <= low_stock_threshold THEN 'LOW_STOCK'
                  ELSE 'ACTIVE' END;
-- một vài slot bị tắt thủ công
UPDATE MachineSlot SET status = 'DISABLED' WHERE MachineSlotID % 37 = 0;

DROP TABLE #S, #Inv;

SELECT 'Orders' AS TableName, COUNT(*) AS Total FROM Orders
UNION ALL SELECT 'Payment', COUNT(*) FROM Payment
UNION ALL SELECT 'DispenseTransaction', COUNT(*) FROM DispenseTransaction
UNION ALL SELECT 'InventoryLog', COUNT(*) FROM InventoryLog;

DECLARE @elapsed int = DATEDIFF(SECOND, @t0, SYSDATETIME());
RAISERROR('>> HOAN TAT file 3. Thoi gian: %d giay', 0, 1, @elapsed) WITH NOWAIT;
GO

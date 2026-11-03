/* =====================================================================
   Du lieu van hanh + index + tong ket + truy van kiem tra
   Alert, MaintenanceRecord, DeviceEvent, AuditLog
   Chay sau file 03.
   ===================================================================== */
USE ScentStationDB;
GO
IF NOT EXISTS (SELECT 1 FROM Orders)
BEGIN
    RAISERROR('Chua co du lieu Orders. Hay chay file 03 truoc.', 16, 1);
    RETURN;
END
IF EXISTS (SELECT 1 FROM Alert)
BEGIN
    RAISERROR('Du lieu van hanh da ton tai. Chay lai tu file 01 neu muon lam moi.', 16, 1);
    RETURN;
END
SET NOCOUNT ON;
DECLARE @t0 datetime2 = SYSDATETIME();
DECLARE @TotalAlerts       int = 2500;    -- canh bao (kem phieu bao tri)
DECLARE @TotalPreventive   int = 400;     -- phieu bao tri dinh ky
DECLARE @TotalDeviceEvents int = 25000;   -- su kien thiet bi
DECLARE @TotalAuditLogs    int = 12000;   -- nhat ky audit

DECLARE @i int, @r int, @k int, @sid int, @mid int, @brand int, @adj int, @roll int;
DECLARE @created datetime2;

SELECT ROW_NUMBER() OVER (ORDER BY s.MachineSlotID) AS rn, s.MachineSlotID, s.MachineID, m.BrandID
INTO #S FROM MachineSlot s JOIN Machine m ON m.MachineID = s.MachineID;
DECLARE @slotCount int = (SELECT COUNT(*) FROM #S);

SELECT ROW_NUMBER() OVER (ORDER BY MachineID) AS rn, MachineID, serial_number INTO #M FROM Machine;
DECLARE @machCount int = (SELECT COUNT(*) FROM #M);

SELECT UserID, BrandID, brand_role INTO #Staff FROM BrandMember;

SELECT ROW_NUMBER() OVER (ORDER BY u.UserID) AS rn, u.UserID, bm.BrandID
INTO #UB FROM [User] u LEFT JOIN BrandMember bm ON bm.UserID = u.UserID;
DECLARE @ubCount int = (SELECT COUNT(*) FROM #UB);

/* ---------- 3.2 Alert + MaintenanceRecord ---------- */
DECLARE @atype varchar(30), @sev varchar(20), @ast varchar(20), @mtype varchar(30);
DECLARE @ack datetime2, @res datetime2, @aid int, @ops int, @tech int, @slotForAlert int;
SET @i = 0;
WHILE @i < @TotalAlerts
BEGIN
    SET @i += 1;
    SET @r = 1 + ABS(CHECKSUM(NEWID())) % @slotCount;
    SELECT @sid = MachineSlotID, @mid = MachineID, @brand = BrandID FROM #S WHERE rn = @r;

    SET @k = 1 + ABS(CHECKSUM(NEWID())) % 7;
    SET @atype = CHOOSE(@k, 'LOW_STOCK', 'MACHINE_OFFLINE', 'DOOR_OPEN', 'LEAKAGE_SUSPECTED',
                            'SENSOR_FAILURE', 'ACTUATOR_FAILURE', 'DISPENSE_FAILURE');
    SET @sev   = CHOOSE(@k, 'MEDIUM', 'HIGH', 'MEDIUM', 'CRITICAL', 'HIGH', 'CRITICAL', 'MEDIUM');
    SET @mtype = CHOOSE(@k, 'REFILL_SUPPORT', 'INSPECTION', 'INSPECTION', 'REPAIR',
                            'PART_REPLACEMENT', 'REPAIR', 'CALIBRATION');
    SET @slotForAlert = CASE WHEN @k IN (2, 3) THEN NULL ELSE @sid END;

    SET @created = DATEADD(MINUTE, -(2880 + ABS(CHECKSUM(NEWID())) % 83520), SYSDATETIME());
    SET @roll = ABS(CHECKSUM(NEWID())) % 100;
    SET @ast = CASE WHEN @roll < 70 THEN 'RESOLVED' WHEN @roll < 85 THEN 'ACKNOWLEDGED' ELSE 'OPEN' END;
    SET @ack = CASE WHEN @ast <> 'OPEN' THEN DATEADD(MINUTE, 5 + ABS(CHECKSUM(NEWID())) % 55, @created) END;
    SET @res = CASE WHEN @ast = 'RESOLVED' THEN DATEADD(MINUTE, 60 + ABS(CHECKSUM(NEWID())) % 1400, @ack) END;

    INSERT Alert(MachineID, MachineSlotID, alert_type, severity, created_at, acknowledged_at, resolved_at, status)
    VALUES (@mid, @slotForAlert, @atype, @sev, @created, @ack, @res, @ast);
    SET @aid = SCOPE_IDENTITY();

    IF @sev IN ('HIGH', 'CRITICAL') OR ABS(CHECKSUM(NEWID())) % 100 < 15
    BEGIN
        SELECT TOP 1 @ops  = UserID FROM #Staff WHERE BrandID = @brand AND brand_role = 'OPS_MANAGER';
        SELECT TOP 1 @tech = UserID FROM #Staff WHERE BrandID = @brand AND brand_role = 'TECHNICIAN' ORDER BY NEWID();

        INSERT MaintenanceRecord(AlertID, MachineID, CreatedByUserID, AssignedToUserID, maintenance_type,
                                 description, status, created_at, completed_at)
        VALUES (@aid, @mid, @ops, @tech, @mtype,
                'Xu ly canh bao ' + @atype + ' tren may #' + CAST(@mid AS varchar(10)),
                CASE @ast WHEN 'RESOLVED' THEN 'COMPLETED' WHEN 'ACKNOWLEDGED' THEN 'IN_PROGRESS' ELSE 'OPEN' END,
                DATEADD(MINUTE, 10, @created), @res);
    END

    IF @i % 1000 = 0
        RAISERROR('>> Alerts: %d / %d', 0, 1, @i, @TotalAlerts) WITH NOWAIT;
END

-- Bảo trì định kỳ (không gắn alert)
SET @i = 0;
WHILE @i < @TotalPreventive
BEGIN
    SET @i += 1;
    SET @r = 1 + ABS(CHECKSUM(NEWID())) % @machCount;
    SELECT @mid = MachineID FROM #M WHERE rn = @r;
    SELECT @brand = BrandID FROM Machine WHERE MachineID = @mid;
    SELECT TOP 1 @ops  = UserID FROM #Staff WHERE BrandID = @brand AND brand_role = 'OPS_MANAGER';
    SELECT TOP 1 @tech = UserID FROM #Staff WHERE BrandID = @brand AND brand_role = 'TECHNICIAN' ORDER BY NEWID();
    SET @created = DATEADD(MINUTE, -(2880 + ABS(CHECKSUM(NEWID())) % 83520), SYSDATETIME());
    SET @roll = ABS(CHECKSUM(NEWID())) % 100;

    INSERT MaintenanceRecord(AlertID, MachineID, CreatedByUserID, AssignedToUserID, maintenance_type,
                             description, status, created_at, completed_at)
    VALUES (NULL, @mid, @ops, @tech, 'INSPECTION', 'Kiem tra dinh ky va ve sinh dau phun',
            CASE WHEN @roll < 85 THEN 'COMPLETED' WHEN @roll < 95 THEN 'IN_PROGRESS' ELSE 'OPEN' END,
            @created,
            CASE WHEN @roll < 85 THEN DATEADD(MINUTE, 90, @created) END);
END
RAISERROR('>> Da nap xong Alert + MaintenanceRecord', 0, 1) WITH NOWAIT;

/* ---------- 3.3 DeviceEvent ---------- */
DECLARE @serial varchar(100), @etype varchar(30);
SET @i = 0;
WHILE @i < @TotalDeviceEvents
BEGIN
    SET @i += 1;
    SET @r = 1 + ABS(CHECKSUM(NEWID())) % @machCount;
    SELECT @mid = MachineID, @serial = serial_number FROM #M WHERE rn = @r;
    SET @k = 1 + ABS(CHECKSUM(NEWID())) % 10;
    SET @etype = CHOOSE(@k, 'STARTUP', 'SHUTDOWN', 'RECONNECT', 'HEARTBEAT_LOST', 'MAINTENANCE_MODE',
                            'SENSOR_ERROR', 'DISPENSE_FAILURE', 'FIRMWARE_UPDATE', 'DOOR_OPENED', 'DOOR_CLOSED');

    INSERT DeviceEvent(MachineID, event_type, message, created_at)
    VALUES (@mid, @etype, 'Machine ' + @serial + ' reported ' + @etype,
            DATEADD(SECOND, -(ABS(CHECKSUM(NEWID())) % 7776000), SYSDATETIME()));

    IF @i % 5000 = 0
        RAISERROR('>> DeviceEvent: %d / %d', 0, 1, @i, @TotalDeviceEvents) WITH NOWAIT;
END

/* ---------- 3.4 AuditLog ---------- */
DECLARE @uid int, @entityId int;
SET @i = 0;
WHILE @i < @TotalAuditLogs
BEGIN
    SET @i += 1;
    SET @r = 1 + ABS(CHECKSUM(NEWID())) % @ubCount;
    SELECT @uid = UserID, @brand = BrandID FROM #UB WHERE rn = @r;
    SET @k = 1 + ABS(CHECKSUM(NEWID())) % 8;
    SET @entityId = 1 + ABS(CHECKSUM(NEWID())) % 100;
    SET @adj = ABS(CHECKSUM(NEWID())) % 50000;

    INSERT AuditLog(UserID, BrandID, action, entity_type, entity_id, old_value, new_value, created_at)
    VALUES (@uid, @brand,
            CHOOSE(@k, 'LOGIN', 'UPDATE_PRICE', 'REFILL_SLOT', 'ADJUST_INVENTORY', 'CHANGE_ROLE',
                       'DISABLE_MACHINE', 'REFUND_ORDER', 'CREATE_TICKET'),
            CHOOSE(@k, 'User', 'Perfume', 'MachineSlot', 'InventoryLog', 'BrandMember',
                       'Machine', 'Orders', 'MaintenanceRecord'),
            @entityId,
            CASE WHEN @k = 1 THEN NULL ELSE N'{"value":' + CAST(@adj AS nvarchar(20)) + N'}' END,
            CASE WHEN @k = 1 THEN NULL ELSE N'{"value":' + CAST(@adj + 5000 AS nvarchar(20)) + N'}' END,
            DATEADD(SECOND, -(ABS(CHECKSUM(NEWID())) % 7776000), SYSDATETIME()));

    IF @i % 4000 = 0
        RAISERROR('>> AuditLog: %d / %d', 0, 1, @i, @TotalAuditLogs) WITH NOWAIT;
END

/* ---------- 3.5 Index hỗ trợ báo cáo (tạo sau khi nạp để nạp nhanh hơn) ---------- */
CREATE INDEX IX_Orders_Slot_Created   ON Orders(MachineSlotID, created_at);
CREATE INDEX IX_Orders_Status         ON Orders(status, created_at);
CREATE INDEX IX_Payment_Order         ON Payment(OrderID);
CREATE INDEX IX_InvLog_Slot_Created   ON InventoryLog(MachineSlotID, created_at);
CREATE INDEX IX_InvLog_Order          ON InventoryLog(OrderID);
CREATE INDEX IX_Alert_Machine_Status  ON Alert(MachineID, status);
CREATE INDEX IX_Maint_Machine         ON MaintenanceRecord(MachineID, status);
CREATE INDEX IX_DevEvent_Machine_Time ON DeviceEvent(MachineID, created_at);
CREATE INDEX IX_Audit_Created         ON AuditLog(created_at);
CREATE INDEX IX_Machine_Brand         ON Machine(BrandID, status);
CREATE INDEX IX_Perfume_Brand         ON Perfume(BrandID);
CREATE INDEX IX_Location_Brand        ON Location(BrandID);

DROP TABLE #S, #M, #Staff, #UB;

/* ---------- Tổng kết ---------- */
SELECT 'User' AS TableName, COUNT(*) AS Total FROM [User]
UNION ALL SELECT 'Brand', COUNT(*) FROM Brand
UNION ALL SELECT 'BrandMember', COUNT(*) FROM BrandMember
UNION ALL SELECT 'Location', COUNT(*) FROM Location
UNION ALL SELECT 'Perfume', COUNT(*) FROM Perfume
UNION ALL SELECT 'Machine', COUNT(*) FROM Machine
UNION ALL SELECT 'MachineSlot', COUNT(*) FROM MachineSlot
UNION ALL SELECT 'Orders', COUNT(*) FROM Orders
UNION ALL SELECT 'Payment', COUNT(*) FROM Payment
UNION ALL SELECT 'DispenseTransaction', COUNT(*) FROM DispenseTransaction
UNION ALL SELECT 'InventoryLog', COUNT(*) FROM InventoryLog
UNION ALL SELECT 'Alert', COUNT(*) FROM Alert
UNION ALL SELECT 'MaintenanceRecord', COUNT(*) FROM MaintenanceRecord
UNION ALL SELECT 'DeviceEvent', COUNT(*) FROM DeviceEvent
UNION ALL SELECT 'AuditLog', COUNT(*) FROM AuditLog;

DECLARE @elapsed int = DATEDIFF(SECOND, @t0, SYSDATETIME());
RAISERROR('>> HOAN TAT. Thoi gian nap du lieu: %d giay', 0, 1, @elapsed) WITH NOWAIT;
GO

/* =====================================================================
   PHẦN 4: TRUY VẤN KIỂM TRA MẪU
   ===================================================================== */

-- 1) Đơn đã thanh toán nhưng xịt thất bại / không xác nhận (cần review hoặc hoàn tiền)
SELECT o.OrderID, o.payment_reference, o.status AS order_status, p.status AS payment_status,
       d.status AS dispense_status, d.error_message
FROM Orders o
JOIN Payment p ON p.OrderID = o.OrderID AND p.status IN ('SUCCESS', 'REFUNDED')
JOIN DispenseTransaction d ON d.OrderID = o.OrderID AND d.status IN ('FAILED', 'UNCERTAIN')
ORDER BY o.created_at DESC;

-- 2) Doanh thu theo brand (chỉ tính đơn xịt thành công)
SELECT b.name AS brand, COUNT(*) AS so_don, SUM(o.amount) AS doanh_thu
FROM Orders o
JOIN MachineSlot s ON s.MachineSlotID = o.MachineSlotID
JOIN Machine m ON m.MachineID = s.MachineID
JOIN Brand b ON b.BrandID = m.BrandID
WHERE o.status = 'DISPENSED'
GROUP BY b.name
ORDER BY doanh_thu DESC;

-- 3) Slot sắp hết nước hoa
SELECT m.name AS machine, s.slot_number, p.name AS perfume, s.quantity, s.low_stock_threshold, s.status
FROM MachineSlot s
JOIN Machine m ON m.MachineID = s.MachineID
JOIN Perfume p ON p.PerfumeID = s.PerfumeID
WHERE s.status IN ('LOW_STOCK', 'EMPTY')
ORDER BY s.quantity;
GO

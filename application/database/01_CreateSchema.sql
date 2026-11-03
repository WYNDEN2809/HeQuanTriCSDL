/* =====================================================================
   Tao CSDL ScentStationDB + 15 bang
   Chay file nay DAU TIEN. Se xoa va tao lai database neu da ton tai.
   ===================================================================== */

USE master;
GO
IF DB_ID('ScentStationDB') IS NOT NULL
BEGIN
    ALTER DATABASE ScentStationDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ScentStationDB;
END
GO
CREATE DATABASE ScentStationDB;
GO
USE ScentStationDB;
GO

/* =====================================================================
   TẠO BẢNG
   ===================================================================== */

CREATE TABLE [User] (
    UserID        int IDENTITY(1,1) CONSTRAINT PK_User PRIMARY KEY,
    username      varchar(50)  NOT NULL CONSTRAINT UQ_User_username UNIQUE,
    email         varchar(254) NOT NULL CONSTRAINT UQ_User_email UNIQUE,
    password_hash varchar(255) NOT NULL,
    role          varchar(20)  NOT NULL CONSTRAINT CK_User_role CHECK (role IN ('SUPER_ADMIN','USER')),
    is_active     bit          NOT NULL CONSTRAINT DF_User_active DEFAULT 1
);

CREATE TABLE Brand (
    BrandID     int IDENTITY(1,1) CONSTRAINT PK_Brand PRIMARY KEY,
    name        varchar(100) NOT NULL CONSTRAINT UQ_Brand_name UNIQUE,
    description varchar(500) NULL,
    logo_url    varchar(255) NULL,
    is_active   bit          NOT NULL CONSTRAINT DF_Brand_active DEFAULT 1
);

CREATE TABLE BrandMember (
    BrandMemberID int IDENTITY(1,1) CONSTRAINT PK_BrandMember PRIMARY KEY,
    UserID        int NOT NULL CONSTRAINT FK_BrandMember_User  REFERENCES [User](UserID),
    BrandID       int NOT NULL CONSTRAINT FK_BrandMember_Brand REFERENCES Brand(BrandID),
    brand_role    varchar(20) NOT NULL CONSTRAINT CK_BrandMember_role
        CHECK (brand_role IN ('BRAND_ADMIN','OPS_MANAGER','TECHNICIAN','INVENTORY_STAFF','VIEWER')),
    CONSTRAINT UQ_BrandMember UNIQUE (UserID, BrandID)
);

CREATE TABLE Location (
    LocationID  int IDENTITY(1,1) CONSTRAINT PK_Location PRIMARY KEY,
    BrandID     int NOT NULL CONSTRAINT FK_Location_Brand REFERENCES Brand(BrandID),
    name        varchar(100) NOT NULL,
    address     varchar(255) NULL,
    is_active   bit NOT NULL CONSTRAINT DF_Location_active DEFAULT 1,
    description varchar(500) NULL
);

CREATE TABLE Perfume (
    PerfumeID       int IDENTITY(1,1) CONSTRAINT PK_Perfume PRIMARY KEY,
    BrandID         int NOT NULL CONSTRAINT FK_Perfume_Brand REFERENCES Brand(BrandID),
    name            varchar(150) NOT NULL,
    description     varchar(500) NULL,
    is_active       bit NOT NULL CONSTRAINT DF_Perfume_active DEFAULT 1,
    price_per_spray decimal(10,2) NOT NULL CONSTRAINT CK_Perfume_price CHECK (price_per_spray >= 0)
);

CREATE TABLE Machine (
    MachineID     int IDENTITY(1,1) CONSTRAINT PK_Machine PRIMARY KEY,
    BrandID       int NOT NULL CONSTRAINT FK_Machine_Brand    REFERENCES Brand(BrandID),
    LocationID    int NOT NULL CONSTRAINT FK_Machine_Location REFERENCES Location(LocationID),
    name          varchar(100) NOT NULL,
    status        varchar(20)  NOT NULL CONSTRAINT CK_Machine_status
        CHECK (status IN ('ONLINE','OFFLINE','MAINTENANCE','DISABLED','ERROR')),
    serial_number varchar(100) NOT NULL CONSTRAINT UQ_Machine_serial UNIQUE,
    last_seen_at  datetime2 NULL
);

CREATE TABLE MachineSlot (
    MachineSlotID       int IDENTITY(1,1) CONSTRAINT PK_MachineSlot PRIMARY KEY,
    PerfumeID           int NOT NULL CONSTRAINT FK_MachineSlot_Perfume REFERENCES Perfume(PerfumeID),
    MachineID           int NOT NULL CONSTRAINT FK_MachineSlot_Machine REFERENCES Machine(MachineID),
    slot_number         int NOT NULL,
    quantity            int NOT NULL CONSTRAINT CK_Slot_qty CHECK (quantity >= 0),
    price_per_spray     decimal(10,2) NOT NULL,
    low_stock_threshold int NOT NULL,
    spray_duration      int NOT NULL,          -- mili giây
    capacity            int NOT NULL,          -- số lần xịt tối đa của chai
    status              varchar(20) NOT NULL CONSTRAINT CK_Slot_status
        CHECK (status IN ('ACTIVE','LOW_STOCK','EMPTY','DISABLED')),
    CONSTRAINT UQ_Slot_Machine_Number UNIQUE (MachineID, slot_number)
);

CREATE TABLE Alert (
    AlertID        int IDENTITY(1,1) CONSTRAINT PK_Alert PRIMARY KEY,
    MachineID      int NOT NULL CONSTRAINT FK_Alert_Machine REFERENCES Machine(MachineID),
    MachineSlotID  int NULL     CONSTRAINT FK_Alert_Slot    REFERENCES MachineSlot(MachineSlotID),
    alert_type     varchar(30) NOT NULL,
    severity       varchar(20) NOT NULL CONSTRAINT CK_Alert_severity CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    created_at     datetime2 NOT NULL CONSTRAINT DF_Alert_created DEFAULT SYSDATETIME(),
    acknowledged_at datetime2 NULL,
    resolved_at    datetime2 NULL,
    status         varchar(20) NOT NULL CONSTRAINT CK_Alert_status CHECK (status IN ('OPEN','ACKNOWLEDGED','RESOLVED'))
);

CREATE TABLE MaintenanceRecord (
    MaintenanceRecordID int IDENTITY(1,1) CONSTRAINT PK_Maintenance PRIMARY KEY,
    AlertID             int NULL     CONSTRAINT FK_Maint_Alert   REFERENCES Alert(AlertID),
    MachineID           int NOT NULL CONSTRAINT FK_Maint_Machine REFERENCES Machine(MachineID),
    CreatedByUserID     int NOT NULL CONSTRAINT FK_Maint_Creator REFERENCES [User](UserID),
    AssignedToUserID    int NULL     CONSTRAINT FK_Maint_Assignee REFERENCES [User](UserID),
    maintenance_type    varchar(30) NOT NULL,
    description         varchar(500) NULL,
    status              varchar(20) NOT NULL CONSTRAINT CK_Maint_status
        CHECK (status IN ('OPEN','IN_PROGRESS','COMPLETED','CANCELLED')),
    created_at          datetime2 NOT NULL CONSTRAINT DF_Maint_created DEFAULT SYSDATETIME(),
    completed_at        datetime2 NULL
);

CREATE TABLE Orders (
    OrderID           int IDENTITY(1,1) CONSTRAINT PK_Orders PRIMARY KEY,
    MachineSlotID     int NOT NULL CONSTRAINT FK_Orders_Slot    REFERENCES MachineSlot(MachineSlotID),
    PerfumeID         int NOT NULL CONSTRAINT FK_Orders_Perfume REFERENCES Perfume(PerfumeID),
    unit_price        decimal(10,2) NOT NULL,
    quantity          int NOT NULL CONSTRAINT DF_Orders_qty DEFAULT 1,
    amount            decimal(10,2) NOT NULL,
    payment_reference varchar(100) NOT NULL CONSTRAINT UQ_Orders_payref UNIQUE,
    currency          varchar(10) NOT NULL CONSTRAINT DF_Orders_cur DEFAULT 'VND',
    status            varchar(20) NOT NULL CONSTRAINT CK_Orders_status
        CHECK (status IN ('PENDING','DISPENSED','DISPENSE_FAILED','REFUNDED','REVIEW','EXPIRED','CANCELLED','FAILED')),
    expires_at        datetime2 NOT NULL,
    created_at        datetime2 NOT NULL CONSTRAINT DF_Orders_created DEFAULT SYSDATETIME()
);

CREATE TABLE Payment (
    PaymentID               int IDENTITY(1,1) CONSTRAINT PK_Payment PRIMARY KEY,
    OrderID                 int NOT NULL CONSTRAINT FK_Payment_Order REFERENCES Orders(OrderID),
    method                  varchar(20) NOT NULL,
    provider_transaction_id varchar(100) NOT NULL CONSTRAINT UQ_Payment_provider UNIQUE,
    amount                  decimal(10,2) NOT NULL,
    status                  varchar(20) NOT NULL CONSTRAINT CK_Payment_status
        CHECK (status IN ('PENDING','SUCCESS','FAILED','CANCELLED','REFUNDED')),
    paid_at                 datetime2 NULL,
    created_at              datetime2 NOT NULL CONSTRAINT DF_Payment_created DEFAULT SYSDATETIME()
);

-- Mỗi đơn hàng chỉ có tối đa 1 lệnh xịt (UNIQUE OrderID) => đúng business rule "no more than one spray"
CREATE TABLE DispenseTransaction (
    DispenseTransactionID int IDENTITY(1,1) CONSTRAINT PK_Dispense PRIMARY KEY,
    OrderID               int NOT NULL CONSTRAINT FK_Dispense_Order REFERENCES Orders(OrderID)
                              CONSTRAINT UQ_Dispense_Order UNIQUE,
    status                varchar(20) NOT NULL CONSTRAINT CK_Dispense_status
        CHECK (status IN ('PENDING','SUCCESS','FAILED','UNCERTAIN')),
    command_id            varchar(100) NOT NULL CONSTRAINT UQ_Dispense_cmd UNIQUE,
    error_message         varchar(500) NULL,
    expires_at            datetime2 NOT NULL,
    acknowledged_at       datetime2 NULL,
    executed_at           datetime2 NULL,
    created_at            datetime2 NOT NULL CONSTRAINT DF_Dispense_created DEFAULT SYSDATETIME()
);

CREATE TABLE InventoryLog (
    InventoryLogID  int IDENTITY(1,1) CONSTRAINT PK_InventoryLog PRIMARY KEY,
    UserID          int NULL     CONSTRAINT FK_InvLog_User  REFERENCES [User](UserID),
    MachineSlotID   int NOT NULL CONSTRAINT FK_InvLog_Slot  REFERENCES MachineSlot(MachineSlotID),
    OrderID         int NULL     CONSTRAINT FK_InvLog_Order REFERENCES Orders(OrderID),
    change_type     varchar(30) NOT NULL,
    quantity_before int NOT NULL,
    quantity_after  int NOT NULL,
    change_amount   int NOT NULL,
    reason          varchar(30) NULL,
    created_at      datetime2 NOT NULL CONSTRAINT DF_InvLog_created DEFAULT SYSDATETIME()
);

CREATE TABLE DeviceEvent (
    DeviceEventID int IDENTITY(1,1) CONSTRAINT PK_DeviceEvent PRIMARY KEY,
    MachineID     int NOT NULL CONSTRAINT FK_DevEvent_Machine REFERENCES Machine(MachineID),
    event_type    varchar(30) NOT NULL,
    message       varchar(500) NULL,
    created_at    datetime2 NOT NULL CONSTRAINT DF_DevEvent_created DEFAULT SYSDATETIME()
);

CREATE TABLE AuditLog (
    AuditLogID  int IDENTITY(1,1) CONSTRAINT PK_AuditLog PRIMARY KEY,
    UserID      int NULL CONSTRAINT FK_Audit_User  REFERENCES [User](UserID),
    BrandID     int NULL CONSTRAINT FK_Audit_Brand REFERENCES Brand(BrandID),
    action      varchar(100) NOT NULL,
    entity_type varchar(50)  NULL,
    entity_id   int NULL,
    old_value   nvarchar(max) NULL,
    new_value   nvarchar(max) NULL,
    created_at  datetime2 NOT NULL CONSTRAINT DF_Audit_created DEFAULT SYSDATETIME()
);
GO

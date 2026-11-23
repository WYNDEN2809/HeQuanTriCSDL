/* =====================================================================
   FILE 05 - Them bang MaintenanceChecklistItem (checklist phieu bao tri)
   Dung cho database DA TAO truoc do (chay sau 01..04). Chay lai nhieu lan van an toan.
   Database moi: file 01_CreateSchema.sql da gom san bang nay (khong can chay file 05).
   ===================================================================== */
USE ScentStationDB;
GO
IF OBJECT_ID('dbo.MaintenanceChecklistItem', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.MaintenanceChecklistItem (
        ChecklistItemID     int IDENTITY(1,1) CONSTRAINT PK_ChecklistItem PRIMARY KEY,
        MaintenanceRecordID int NOT NULL CONSTRAINT FK_Checklist_Record REFERENCES dbo.MaintenanceRecord(MaintenanceRecordID),
        phase               varchar(20) NOT NULL CONSTRAINT CK_Checklist_phase
            CHECK (phase IN ('INSPECTION','REPAIR','REFILL_SUPPORT','POST_MAINTENANCE','RESULT')),
        item_text           nvarchar(200) NOT NULL,
        is_done             bit NOT NULL CONSTRAINT DF_Checklist_done DEFAULT 0,
        DoneByUserID        int NULL CONSTRAINT FK_Checklist_User REFERENCES dbo.[User](UserID),
        done_at             datetime2 NULL,
        note                nvarchar(500) NULL,
        sort_order          int NOT NULL CONSTRAINT DF_Checklist_sort DEFAULT 0
    );
    CREATE INDEX IX_Checklist_Record ON dbo.MaintenanceChecklistItem(MaintenanceRecordID);
    PRINT 'Da tao bang MaintenanceChecklistItem';
END
ELSE
    PRINT 'Bang MaintenanceChecklistItem da ton tai - bo qua';
GO

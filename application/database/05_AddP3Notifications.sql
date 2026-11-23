/* P3: persisted in-app notifications for alert creation, assignment, and SLA escalation. */
IF OBJECT_ID(N'dbo.Notification', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Notification (
        NotificationID int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Notification PRIMARY KEY,
        UserID int NOT NULL CONSTRAINT FK_Notification_User REFERENCES dbo.[User](UserID),
        BrandID int NOT NULL CONSTRAINT FK_Notification_Brand REFERENCES dbo.Brand(BrandID),
        event_key varchar(120) NOT NULL,
        title nvarchar(200) NOT NULL,
        message nvarchar(1000) NOT NULL,
        target_url nvarchar(300) NOT NULL,
        created_at datetime2 NOT NULL CONSTRAINT DF_Notification_created DEFAULT SYSDATETIME(),
        read_at datetime2 NULL,
        external_sent_at datetime2 NULL,
        CONSTRAINT UQ_Notification_User_Event UNIQUE(UserID, event_key)
    );
    CREATE INDEX IX_Notification_User_Read_Created
        ON dbo.Notification(UserID, read_at, created_at DESC);
END;
GO

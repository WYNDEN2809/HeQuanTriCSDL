/* =====================================================================
   FILE 06 - Them bang Campaign + cot Orders.CampaignID (khuyen mai / dung thu mien phi / gia tam thoi)
   Dung cho database DA TAO truoc do (chay sau 01..05). Chay lai nhieu lan van an toan.
   Database moi: file 01_CreateSchema.sql da gom san (khong can chay file 06).
   ===================================================================== */
USE ScentStationDB;
GO
IF OBJECT_ID('dbo.Campaign', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Campaign (
        CampaignID    int IDENTITY(1,1) CONSTRAINT PK_Campaign PRIMARY KEY,
        BrandID       int NOT NULL CONSTRAINT FK_Campaign_Brand REFERENCES dbo.Brand(BrandID),
        PerfumeID     int NULL     CONSTRAINT FK_Campaign_Perfume REFERENCES dbo.Perfume(PerfumeID),
        LocationID    int NULL     CONSTRAINT FK_Campaign_Location REFERENCES dbo.Location(LocationID),
        name          varchar(100) NOT NULL,
        campaign_type varchar(20)  NOT NULL CONSTRAINT CK_Campaign_type CHECK (campaign_type IN ('PERCENT_OFF','TEMP_PRICE','FREE_TRIAL')),
        value         decimal(10,2) NULL,
        starts_at     datetime2 NOT NULL,
        ends_at       datetime2 NOT NULL,
        is_active     bit NOT NULL CONSTRAINT DF_Campaign_active DEFAULT 1,
        created_at    datetime2 NOT NULL CONSTRAINT DF_Campaign_created DEFAULT SYSDATETIME(),
        CONSTRAINT CK_Campaign_period CHECK (ends_at > starts_at)
    );
    CREATE INDEX IX_Campaign_Brand ON dbo.Campaign(BrandID, is_active, starts_at, ends_at);
    PRINT 'Da tao bang Campaign';
END
ELSE
    PRINT 'Bang Campaign da ton tai - bo qua';
GO
IF COL_LENGTH('dbo.Orders', 'CampaignID') IS NULL
BEGIN
    ALTER TABLE dbo.Orders ADD CampaignID int NULL CONSTRAINT FK_Orders_Campaign REFERENCES dbo.Campaign(CampaignID);
    PRINT 'Da them cot Orders.CampaignID';
END
ELSE
    PRINT 'Cot Orders.CampaignID da ton tai - bo qua';
GO

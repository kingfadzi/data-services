-- Idempotent: confirm Full-Text Search is installed and create the default catalog.
-- Per-table full-text indexes belong to whoever owns the schema, not here.
IF SERVERPROPERTY('IsFullTextInstalled') <> 1
BEGIN
    RAISERROR('Full-Text Search is not installed in this SQL Server image.', 16, 1);
END
GO

USE [$(DB)];
GO

IF NOT EXISTS (SELECT 1 FROM sys.fulltext_catalogs WHERE name = N'$(DB)_ft')
    CREATE FULLTEXT CATALOG [$(DB)_ft] AS DEFAULT;
GO

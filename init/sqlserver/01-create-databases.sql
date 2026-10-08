-- Create the application database and its login. Runs once per database on first start, as sa.
-- $(DB), $(USERNAME) and $(PASSWORD) are supplied by the entrypoint from .env and /run/secrets.
-- Every statement is re-runnable: a failed init is retried, and new numbered scripts are applied
-- to existing volumes.
IF DB_ID('$(DB)') IS NULL
    CREATE DATABASE [$(DB)];
GO

IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = N'$(USERNAME)')
    CREATE LOGIN [$(USERNAME)] WITH PASSWORD = '$(PASSWORD)', CHECK_POLICY = ON;
GO

USE [$(DB)];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'$(USERNAME)')
    CREATE USER [$(USERNAME)] FOR LOGIN [$(USERNAME)];
GO

IF IS_ROLEMEMBER('db_owner', '$(USERNAME)') = 0
    ALTER ROLE db_owner ADD MEMBER [$(USERNAME)];
GO

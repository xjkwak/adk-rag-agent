-- =============================================================================
-- Aegis.Database/Procedures/sp_ValidateLineClearance.sql
-- FactoryLogix MES — Line Clearance Validation Procedure
-- Version: 1.4.0 | Last Modified: 2024-03-28
-- =============================================================================

CREATE PROCEDURE [dbo].[sp_ValidateLineClearance]
    @WorkOrderId INT,
    @LineId INT,
    @OperatorId INT,
    @IsCleared BIT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FeederMismatches INT = 0;
    DECLARE @PasteExpired BIT = 0;
    DECLARE @ResidualMaterial BIT = 0;
    DECLARE @OperatorValid BIT = 0;
    DECLARE @CertExpired BIT = 0;

    -- Check 1: Feeder-BoM alignment
    SELECT @FeederMismatches = COUNT(*)
    FROM WorkOrderBom wb
    LEFT JOIN FeederSetups fs
        ON wb.PartId = fs.PartId
        AND fs.LineId = @LineId
        AND fs.Position = wb.DesignatedPosition
    WHERE wb.WorkOrderId = @WorkOrderId
      AND fs.Id IS NULL;

    -- Check 2: Solder paste open-life
    -- BUG: Uses DATEADD with 8 hours instead of the 4 hours required by Rule MFG-02.
    IF EXISTS (
        SELECT 1 FROM SolderPaste
        WHERE LineId = @LineId
          AND IsActive = 1
          AND OpenedAt < DATEADD(HOUR, -8, GETUTCDATE())  -- Should be -4, not -8
    )
        SET @PasteExpired = 1;

    -- Check 3: Residual material
    IF EXISTS (
        SELECT 1 FROM FeederSetups
        WHERE LineId = @LineId
          AND WorkOrderId != @WorkOrderId
          AND IsLoaded = 1
    )
        SET @ResidualMaterial = 1;

    -- Check 4: Operator existence
    IF EXISTS (SELECT 1 FROM Operators WHERE Id = @OperatorId AND IsActive = 1)
        SET @OperatorValid = 1;

    -- BUG: Operator certification check is MISSING entirely.
    -- Rule MFG-04 requires IPC-A-610, J-STD-001, or 7711/7721 certification
    -- depending on the process type. This procedure only checks if the operator exists.
    -- A SELECT against OperatorCertifications is needed here.

    -- BUG: No check for active ECOs that might affect this WO (Rule MFG-07).
    -- If an ECO was released while this WO was queued, production could start
    -- with an outdated BoM or routing.

    -- Determine clearance
    SET @IsCleared = CASE
        WHEN @FeederMismatches = 0
         AND @PasteExpired = 0
         AND @ResidualMaterial = 0
         AND @OperatorValid = 1
        THEN 1
        ELSE 0
    END;

    -- Log the result
    INSERT INTO LineClearanceLogs (WorkOrderId, LineId, OperatorId, IsCleared, Timestamp)
    VALUES (@WorkOrderId, @LineId, @OperatorId, @IsCleared, GETUTCDATE());

    -- BUG: No First Article Inspection (FAI) enforcement per Rule MFG-03.
    -- The line clearance can pass without any FAI record for the WO.
    -- This means production can run full speed on a new setup without
    -- verifying the first unit was built correctly.
END

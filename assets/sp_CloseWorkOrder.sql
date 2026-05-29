-- =============================================================================
-- Aegis.Database/Procedures/sp_CloseWorkOrder.sql
-- FactoryLogix MES — Work Order Closure Procedure
-- Version: 2.0.3 | Last Modified: 2024-02-20
-- =============================================================================

CREATE PROCEDURE [dbo].[sp_CloseWorkOrder]
    @WorkOrderId INT,
    @ClosedBy INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CurrentStatus NVARCHAR(20);
    DECLARE @TotalHighValueParts INT;
    DECLARE @RecordedUIDs INT;

    -- Get current WO status
    SELECT @CurrentStatus = Status
    FROM WorkOrders
    WHERE Id = @WorkOrderId;

    -- Basic status validation
    IF @CurrentStatus != 'COMPLETED'
    BEGIN
        RAISERROR('Work Order must be in COMPLETED status to close.', 16, 1);
        RETURN;
    END

    -- BUG: SOP-402 Section 2.3 requires 100% UID coverage for High-Value parts.
    -- The variables below are declared but NEVER USED in a validation check.
    -- The procedure closes the WO regardless of UID completeness.
    SET @TotalHighValueParts = (
        SELECT COUNT(*)
        FROM WorkOrderBom wb
        INNER JOIN Parts p ON wb.PartId = p.Id
        WHERE wb.WorkOrderId = @WorkOrderId
          AND p.CriticalityClass IN ('A', 'B')
    );

    SET @RecordedUIDs = (
        SELECT COUNT(DISTINCT PartId)
        FROM AsBuiltRecords
        WHERE WorkOrderId = @WorkOrderId
          AND UID IS NOT NULL
          AND UID != ''
    );

    -- BUG: This comparison should BLOCK closure if @RecordedUIDs < @TotalHighValueParts.
    -- Instead, it just logs and continues. The WO closes with incomplete as-built data.
    IF @RecordedUIDs < @TotalHighValueParts
        PRINT 'WARNING: Not all High-Value parts have UIDs recorded.';

    -- Close the Work Order
    UPDATE WorkOrders
    SET Status = 'CLOSED',
        ClosedDate = GETUTCDATE(),
        EngineerId = @ClosedBy
    WHERE Id = @WorkOrderId;

    -- BUG: Audit trail gap. Only engineers with ID > 5 generate an audit record.
    -- Junior engineers (ID <= 5) can close WOs with NO audit trail whatsoever.
    -- This violates AS9100D Section 8.5.2 traceability requirements.
    IF @ClosedBy > 5
        INSERT INTO QualityAudit (WOId, Action, PerformedBy, Timestamp)
        VALUES (@WorkOrderId, 'Manual Closure', @ClosedBy, GETUTCDATE());

    -- No check for active ECOs affecting this WO (Rule MFG-07)
    -- No check for open NCRs against this WO (Rule MFG-06)

    PRINT 'Work Order ' + CAST(@WorkOrderId AS NVARCHAR) + ' closed successfully.';
END

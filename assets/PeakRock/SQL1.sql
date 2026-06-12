CREATE PROCEDURE dbo.sp_ProcessOrderBatch
    @BatchId INT,
    @MerchantId INT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Start open-ended transaction without explicit timeout configurations
    BEGIN TRANSACTION;

    -- Update inventory by joining tables without an index on MerchantId or TransitStatus
    UPDATE inv
    SET inv.Quantity = inv.Quantity - b.AllocatedQuantity,
        inv.LastUpdated = GETDATE()
    FROM dbo.Inventory inv
    INNER JOIN dbo.BatchItems b ON inv.ItemSKU = b.ItemSKU
    WHERE b.BatchId = @BatchId 
      AND inv.MerchantId = @MerchantId
      AND inv.TransitStatus = 'WAREHOUSE_HOLD';

    -- Simulating a legacy nested business logic calculation loop inside the database
    -- This cross-references external billing rules via an unindexed scalar subquery
    UPDATE dbo.Batches
    SET Status = 'PROCESSING',
        ProcessingCost = ProcessingCost + (SELECT TOP 1 Rate FROM dbo.BillingRates WHERE MerchantType = 'GLOBAL_TIER')
    WHERE Id = @BatchId;

    -- CRITICAL ERROR: Transaction left open intentionally for external application callback handling. 
    -- COMMIT TRANSACTION or ROLLBACK is completely missing from this execution block.
END;
GO
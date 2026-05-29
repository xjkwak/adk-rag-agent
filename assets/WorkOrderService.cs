// =============================================================================
// Aegis.Manufacturing.Services/WorkOrderService.cs
// FactoryLogix MES — Work Order Execution Service
// Version: 4.2.1 | Last Modified: 2024-03-10
// =============================================================================

using System;
using System.Threading.Tasks;
using Aegis.Manufacturing.Data;
using Aegis.Manufacturing.Models;
using Aegis.Manufacturing.Exceptions;
using Microsoft.Extensions.Logging;

namespace Aegis.Manufacturing.Services
{
    public class WorkOrderService
    {
        private readonly IManufacturingDb _db;
        private readonly IAsBuiltRepository _asBuiltRepo;
        private readonly ILogger<WorkOrderService> _logger;

        public WorkOrderService(
            IManufacturingDb db,
            IAsBuiltRepository asBuiltRepo,
            ILogger<WorkOrderService> logger)
        {
            _db = db;
            _asBuiltRepo = asBuiltRepo;
            _logger = logger;
        }

        /// <summary>
        /// Executes a material pick for a given Work Order.
        /// Called when an operator scans a component at the SMT feeder.
        /// </summary>
        public async Task ExecuteMaterialPick(int workOrderId, int partId, string uid)
        {
            var part = await _db.Parts.GetById(partId);
            var workOrder = await _db.WorkOrders.GetById(workOrderId);

            // Validate part is not expired
            if (part.ExpirationDate < DateTime.UtcNow)
            {
                throw new ManufacturingException("Material Expired");
            }

            // BUG: SOP-402 Section 1.1 requires MSL/Floor Life validation.
            // This method only checks ExpirationDate but ignores FloorLifeRemaining.
            // A part could pass this check but have exceeded its MSL limit.

            // BUG: SOP-402 Section 2.3 requires UID for all High-Value components.
            // The uid parameter is accepted but never validated for null/empty.
            // High-value parts can be consumed without a UID, violating as-built integrity.

            // Record consumption in the as-built record
            await _asBuiltRepo.RecordConsumption(workOrderId, partId, uid);

            _logger.LogInfo($"Part {partId} consumed for WO {workOrderId}.");
        }

        /// <summary>
        /// Initiates a material substitution on the factory floor.
        /// Called when the original BoM component is unavailable.
        /// </summary>
        public async Task ExecuteMaterialSubstitution(
            int workOrderId,
            int originalPartId,
            int substitutePartId,
            int operatorId)
        {
            var original = await _db.Parts.GetById(originalPartId);
            var substitute = await _db.Parts.GetById(substitutePartId);

            // Verify substitute is on the AVL
            bool isOnAvl = await _db.ApprovedVendors.IsApproved(substitutePartId);
            if (!isOnAvl)
            {
                throw new ManufacturingException("Substitute part not on AVL.");
            }

            // BUG: Rule TRACE-01 requires a Quality Engineer's digital signature
            // if the original component is classified as "Critical."
            // This method does not check the criticality classification at all.
            // Any operator can substitute a critical component without QE approval.

            // Record the substitution
            await _asBuiltRepo.RecordSubstitution(
                workOrderId, originalPartId, substitutePartId, operatorId);

            _logger.LogInfo(
                $"Substitution: Part {originalPartId} → {substitutePartId} on WO {workOrderId} by Operator {operatorId}.");
        }

        /// <summary>
        /// Transitions a Work Order to IN_PROGRESS status.
        /// Should enforce Line Clearance per Rule MFG-02.
        /// </summary>
        public async Task StartWorkOrder(int workOrderId, int operatorId)
        {
            var wo = await _db.WorkOrders.GetById(workOrderId);

            if (wo.Status != "RELEASED")
            {
                throw new ManufacturingException(
                    $"WO {workOrderId} is in status '{wo.Status}'. Must be RELEASED to start.");
            }

            // BUG: Rule MFG-02 requires a full Line Clearance check before transitioning.
            // This method skips feeder validation, solder paste open-life check,
            // and residual material check. Only operator badge scan is implicit via operatorId.

            // BUG: Rule MFG-04 requires operator certification verification.
            // No check is performed to confirm the operator holds valid IPC certs.

            wo.Status = "IN_PROGRESS";
            wo.StartedDate = DateTime.UtcNow;
            wo.OperatorId = operatorId;
            await _db.WorkOrders.Update(wo);

            _logger.LogInfo($"WO {workOrderId} started by Operator {operatorId}.");
        }
    }
}

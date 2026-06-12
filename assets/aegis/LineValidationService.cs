// =============================================================================
// Aegis.Manufacturing.Services/LineValidationService.cs
// FactoryLogix MES — Production Line Validation Service
// Version: 3.1.0 | Last Modified: 2024-04-05
// =============================================================================

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Aegis.Manufacturing.Data;
using Aegis.Manufacturing.Models;
using Aegis.Manufacturing.Exceptions;
using Microsoft.Extensions.Logging;

namespace Aegis.Manufacturing.Services
{
    public class LineValidationService
    {
        private readonly IManufacturingDb _db;
        private readonly IEcoRepository _ecoRepo;
        private readonly ICertificationService _certService;
        private readonly ILogger<LineValidationService> _logger;

        public LineValidationService(
            IManufacturingDb db,
            IEcoRepository ecoRepo,
            ICertificationService certService,
            ILogger<LineValidationService> logger)
        {
            _db = db;
            _ecoRepo = ecoRepo;
            _certService = certService;
            _logger = logger;
        }

        /// <summary>
        /// Performs Line Clearance validation before a WO can start.
        /// Per Rule MFG-02, all checks must pass.
        /// </summary>
        public async Task<LineClearanceResult> ValidateLineClearance(
            int workOrderId, int lineId, int operatorId)
        {
            var result = new LineClearanceResult();
            var wo = await _db.WorkOrders.GetById(workOrderId);
            var bom = await _db.WorkOrderBom.GetByWorkOrder(workOrderId);

            // Check 1: Feeder positions match BoM
            var feeders = await _db.FeederSetups.GetByLine(lineId);
            foreach (var bomLine in bom)
            {
                var matchingFeeder = feeders.FirstOrDefault(
                    f => f.PartId == bomLine.PartId && f.Position == bomLine.DesignatedPosition);

                if (matchingFeeder == null)
                {
                    result.AddFailure($"Feeder mismatch: Part {bomLine.PartId} not loaded at position {bomLine.DesignatedPosition}.");
                }
            }

            // Check 2: Solder paste open-life
            // BUG: Rule MFG-02 specifies a 4-hour limit.
            // This code uses 8 hours (480 minutes), which is DOUBLE the allowed time.
            var activePaste = await _db.SolderPaste.GetActiveForLine(lineId);
            if (activePaste != null)
            {
                var openLifeMinutes = (DateTime.UtcNow - activePaste.OpenedAt).TotalMinutes;
                if (openLifeMinutes > 480) // Should be 240 (4 hours), not 480
                {
                    result.AddFailure("Solder paste has exceeded open-life limit.");
                }
            }

            // Check 3: Residual material from previous WO
            // BUG: This check only looks at the current line, not adjacent feeders.
            // Shared feeder banks between lines are not validated.
            var residualParts = await _db.FeederSetups.GetResidualParts(lineId);
            if (residualParts.Any())
            {
                result.AddFailure($"Residual material found: {string.Join(", ", residualParts.Select(p => p.PartId))}");
            }

            // Check 4: Operator badge scan (implicit — operatorId is provided)
            // BUG: Rule MFG-04 requires CERTIFICATION verification, not just badge scan.
            // An operator with an expired IPC-A-610 cert could still start the line.
            var isValidOperator = await _db.Operators.Exists(operatorId);
            if (!isValidOperator)
            {
                result.AddFailure("Operator not found in the system.");
            }

            result.IsCleared = !result.Failures.Any();

            _logger.LogInfo(
                $"Line Clearance for WO {workOrderId} on Line {lineId}: {(result.IsCleared ? "PASSED" : "FAILED")}");

            return result;
        }

        /// <summary>
        /// Checks if any active ECO affects a running Work Order.
        /// Per Rule MFG-07, the line must pause if an ECO impacts the BoM or routing.
        /// </summary>
        public async Task<bool> CheckEcoImpact(int workOrderId)
        {
            var wo = await _db.WorkOrders.GetById(workOrderId);
            var activeEcos = await _ecoRepo.GetActiveEcos();

            foreach (var eco in activeEcos)
            {
                // BUG: This only checks if the ECO affects the same product.
                // It does NOT check if the ECO affects specific BoM line items
                // or process routing steps used by this WO.
                // An ECO that changes a resistor value would not be caught if
                // it's on the same product but a different BoM revision.
                if (eco.ProductId == wo.ProductId && eco.Status == "RELEASED")
                {
                    _logger.LogWarning(
                        $"ECO {eco.Id} may affect WO {workOrderId}. Manual review required.");
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Validates First Article Inspection results per Rule MFG-03.
        /// </summary>
        public async Task<bool> ValidateFirstArticle(int workOrderId, int inspectorId)
        {
            var faiRecord = await _db.FirstArticleInspections.GetByWorkOrder(workOrderId);

            if (faiRecord == null)
            {
                // BUG: Rule MFG-03 requires FAI before full production.
                // If no FAI record exists, this returns false but does NOT block production.
                // The caller (StartWorkOrder) does not check this return value.
                return false;
            }

            // BUG: No validation that the inspector holds the required certification.
            // Rule MFG-04 requires IPC-A-610 for visual inspection.

            // BUG: No check for photo evidence requirement per Rule MFG-03.

            return faiRecord.Status == "PASSED";
        }
    }

    public class LineClearanceResult
    {
        public bool IsCleared { get; set; }
        public List<string> Failures { get; } = new List<string>();

        public void AddFailure(string message)
        {
            Failures.Add(message);
        }
    }
}

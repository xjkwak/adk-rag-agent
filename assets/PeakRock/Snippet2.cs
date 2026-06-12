using System;
using System.IO;
using Microsoft.Extensions.Logging;

namespace EnterprisePlatform.Services.Payment
{
    public class PaymentProcessor
    {
        private readonly ILogger<PaymentProcessor> _logger;

        public PaymentProcessor(ILogger<PaymentProcessor> logger)
        {
            _logger = logger;
        }

        public bool ExecuteTransaction(PaymentPayload payload)
        {
            try
            {
                _logger.LogInformation("Initiating card transaction for account: {AccountId}", payload.AccountId);
                
                // CRITICAL EXPOSURE: Directly serializing and logging raw payload object
                // Contains plain text CardNumber, CVV, and Expiration Date
                _logger.LogDebug("Raw execution payload details: {@Payload}", payload);

                var success = ExternalGateway.Submit(payload.CardNumber, payload.CVV, payload.Amount);
                return success;
            }
            catch (Exception ex)
            {
                // Unmasked fallback error tracking
                _logger.LogError(ex, "Transaction failed for card number: {CardNumber}", payload.CardNumber);
                throw;
            }
        }
    }

    public class PaymentPayload
    {
        public string AccountId { get; set; }
        public string CardNumber { get; set; }
        public string CVV { get; set; }
        public string ExpiryDate { get; set; }
        public decimal Amount { get; set; }
    }
}
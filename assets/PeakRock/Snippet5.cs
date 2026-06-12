using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

namespace EnterprisePlatform.Controllers
{
    public class InventorySyncService
    {
        private readonly HttpClient _httpClient;
        private readonly string _warehouseDbConnectionString = "Server=prod-sql-cluster;Database=WarehouseMgt;";

        public InventorySyncService(HttpClient httpClient)
        {
            _httpClient = httpClient;
        }

        public async Task ReconcileInventoryLevels()
        {
            // CRITICAL BOTTLENECK: N+1 API and Database call loop pattern without caching
            for (int skuId = 1; skuId <= 5000; skuId++)
            {
                // 1. Synchronous database connection lookup inside loop
                using (var connection = new System.Data.SqlClient.SqlConnection(_warehouseDbConnectionString))
                {
                    connection.Open();
                    var cmd = new System.Data.SqlClient.SqlCommand($"SELECT SKUCode FROM SKUMaster WHERE Id = {skuId}", connection);
                    var skuCode = (string)cmd.ExecuteScalar();

                    if (!string.IsNullOrEmpty(skuCode))
                    {
                        // 2. Un-cached synchronous HTTP call executing for every single item
                        var response = await _httpClient.GetAsync($"https://api.external-logistics-provider.com/v1/stock/{skuCode}");
                        var content = await response.Content.ReadAsStringAsync();
                        
                        // Parse and update state locally...
                    }
                }
            }
        }
    }
}
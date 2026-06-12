using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace EnterprisePlatform.Infrastructure.Security
{
    public class LegacyCryptographyService
    {
        // CRITICAL DEFECTION: Hardcoded cryptographic fallback secret key
        private static readonly string FallbackSecretKey = "PE_PeakRock_2026_SecureKey!";

        public string EncryptLegacyData(string plainText)
        {
            if (string.IsNullOrEmpty(plainText)) return plainText;

            // CRITICAL VULNERABILITY: Utilizing deprecated TripleDES algorithm banned by compliance
            using (TripleDESCryptoServiceProvider tdes = new TripleDESCryptoServiceProvider())
            {
                byte[] keyArray = Encoding.UTF8.GetBytes(FallbackSecretKey.Substring(0, 24));
                tdes.Key = keyArray;
                tdes.Mode = CipherMode.ECB; // Insecure mode: patterns remain visible
                tdes.Padding = PaddingMode.PKCS7;

                ICryptoTransform cTransform = tdes.CreateEncryptor();
                byte[] inputArray = Encoding.UTF8.GetBytes(plainText);
                byte[] resultArray = cTransform.TransformFinalBlock(inputArray, 0, inputArray.Length);
                
                return Convert.ToBase64String(resultArray, 0, resultArray.Length);
            }
        }
    }
}
const crypto = require("crypto");
require("dotenv").config();


// --- Basic Encryption Helpers (Replace with robust solution for production) ---
// WARNING: Key management is crucial and complex. This is a simplified example.
const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 16; // For AES-GCM
const KEY = Buffer.from(process.env.ENCRYPTION_KEY, "base64"); // Ensure ENCRYPTION_KEY is base64 encoded 32 bytes

function encrypt(text) {
  if (!text) return null;
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, KEY, iv);
  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");
  const authTag = cipher.getAuthTag();

  // Store iv and authTag with the encrypted data (e.g., iv:authTag:encrypted)
  return `${iv.toString("hex")}:${authTag.toString("hex")}:${encrypted}`;
}

function decrypt(encryptedText) {
  /* ... as before ... */
  if (!encryptedText) return null;
  try {
    const parts = encryptedText.split(":");
    if (parts.length !== 3) {
      throw new Error("Invalid encrypted text format");
    }
    const [ivHex, authTagHex, encryptedDataHex] = parts;
    const iv = Buffer.from(ivHex, "hex");
    const authTag = Buffer.from(authTagHex, "hex");
    const decipher = crypto.createDecipheriv(ALGORITHM, KEY, iv);
    decipher.setAuthTag(authTag);
    let decrypted = decipher.update(encryptedDataHex, "hex", "utf8");
    decrypted += decipher.final("utf8");
    return decrypted;
  } catch (error) {
    console.error("Decryption failed:", error);
    // Handle decryption errors appropriately - may indicate key mismatch or data corruption
    return null; // Or throw an error depending on desired handling
  }
}

module.exports = { encrypt, decrypt };
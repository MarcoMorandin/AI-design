// server.js
require('dotenv').config(); // Load .env file for local development
const express = require('express');
const { createProxyMiddleware, Options } = require('http-proxy-middleware');

const app = express();

// --- Configuration ---
const PORT = process.env.PORT || 3000; // Port for this middleware
const NOUGAT_URL = process.env.NOUGAT_URL; // URL of the actual Nougat service (e.g., http://nougat-container-name:8503)
const VALID_API_KEYS_STRING = process.env.VALID_API_KEYS || ''; // Comma-separated list of valid keys

if (!NOUGAT_URL) {
    console.error("FATAL ERROR: NOUGAT_URL environment variable is not set.");
    process.exit(1);
}
if (!VALID_API_KEYS_STRING) {
    console.warn("WARNING: VALID_API_KEYS environment variable is not set. No API key validation will occur.");
}

const VALID_API_KEYS = VALID_API_KEYS_STRING.split(',').map(key => key.trim()).filter(key => key.length > 0);
console.log(`Nougat Service URL: ${NOUGAT_URL}`);
console.log(`Loaded ${VALID_API_KEYS.length} valid API key(s).`);

// --- API Key Validation Middleware ---
const validateApiKey = (req, res, next) => {
    // Skip validation if no keys are configured (allows easier local testing or internal use)
    if (VALID_API_KEYS.length === 0) {
        console.warn("Skipping API key validation as none are configured.");
        return next();
    }

    const apiKey = req.headers['x-api-key']; // Case-insensitive header checking is handled by Express

    if (!apiKey) {
        console.log("Access denied: Missing X-API-Key header.");
        return res.status(401).json({ error: 'Unauthorized', message: 'Missing API Key' });
    }

    if (!VALID_API_KEYS.includes(apiKey)) {
        console.log(`Access denied: Invalid API Key received: ${apiKey}`);
        return res.status(401).json({ error: 'Unauthorized', message: 'Invalid API Key' });
    }

    // API Key is valid
    console.log(`API Key validated successfully for request to ${req.path}`);
    next(); // Proceed to the next middleware (the proxy)
};

// --- Proxy Middleware Configuration ---
const proxyOptions = {
    target: NOUGAT_URL, // Target host
    changeOrigin: true, // Needed for virtual hosted sites, good practice
    ws: false, // Disable WebSocket proxying unless Nougat uses it (unlikely for standard OCR)
    logLevel: process.env.PROXY_LOG_LEVEL || 'info', // 'debug', 'info', 'warn', 'error', 'silent'
    pathRewrite: {},
    onError: (err, req, res) => {
        console.error('Proxy Error:', err);
        res.writeHead(500, {
            'Content-Type': 'application/json',
        });
        res.end(JSON.stringify({ error: 'Proxy Error', message: 'Could not connect to the upstream server.' }));
    },
    // Optional: Modify request headers before sending to Nougat
    onProxyReq: (proxyReq, req, res) => {
      proxyReq.removeHeader('x-api-key');
      console.log(`Proxying request to: ${NOUGAT_URL}${req.originalUrl || req.url}`);
    }
};

// --- Apply Middleware ---
// 1. Apply API Key Validation to all routes
app.use(validateApiKey);

// 2. Apply the proxy middleware AFTER validation
app.use('/', createProxyMiddleware(proxyOptions));


// --- Start Server ---
app.listen(PORT, () => {
    console.log(`API Gateway running on http://localhost:${PORT}`);
    console.log(`Proxying requests to ${NOUGAT_URL}`);
    if (VALID_API_KEYS.length > 0) {
        console.log("API Key validation is ENABLED.");
    } else {
        console.warn("API Key validation is DISABLED.");
    }
});

// Basic error handler
app.use((err, req, res, next) => {
  console.error("Unhandled Error:", err.stack);
  res.status(500).send('Something broke!');
});
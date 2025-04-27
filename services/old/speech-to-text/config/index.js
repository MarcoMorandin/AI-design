// config/index.js
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs-extra';

dotenv.config();

const config = {
    port: process.env.PORT || 3000,
    mongodbUri: process.env.MONGODB_URI || 'mongodb://localhost:27017',
    mongodbDbName: process.env.MONGODB_DB_NAME || 'node_transcriber_db',
    tempDir: path.resolve(process.env.TEMP_DIR || './temp_files'),
    downloadTimeout: parseInt(process.env.DOWNLOAD_TIMEOUT || '120000', 10),
    groqApiKey: process.env.GROQ_API_KEY,
};

// Ensure temp directory exists
fs.ensureDirSync(config.tempDir);

if (!config.groqApiKey) {
    console.warn("Warning: GROQ_API_KEY is not set in the environment variables. Transcription will fail.");
}

export default config;
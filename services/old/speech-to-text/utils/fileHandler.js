// utils/fileHandler.js
import path from 'path';
import fs from 'fs-extra';
import axios from 'axios';
import config from '../config/index.js';
import { v4 as uuidv4 } from 'uuid';

const getTempAudioPath = (baseFilename) => {
    const stem = path.parse(baseFilename).name;
    return path.join(config.tempDir, `${stem}_extracted_audio.mp3`);
};

const cleanupFiles = async (...filePaths) => {
    for (const filePath of filePaths) {
        if (filePath) {
            try {
                const exists = await fs.pathExists(filePath);
                if (exists) {
                    await fs.remove(filePath);
                    console.log(`Cleaned up temporary file: ${filePath}`);
                }
            } catch (error) {
                console.error(`Error cleaning up file ${filePath}: ${error.message}`);
            }
        }
    }
};

const downloadVideoFromUrl = async (videoUrl, taskId) => {
    let suffix = '.mp4'; // Default suffix
    try {
        const parsedUrl = new URL(videoUrl);
        const pathSuffix = path.extname(parsedUrl.pathname);
        if (pathSuffix && pathSuffix.length > 1 && pathSuffix.length <= 6) {
             // Basic validation for suffix length
            suffix = pathSuffix;
        }
    } catch (e) {
        console.warn(`Could not parse URL path for suffix: ${videoUrl}`);
    }

    const tempFilePath = path.join(config.tempDir, `${taskId}_downloaded${suffix}`);
    console.log(`Attempting to download video from ${videoUrl} to ${tempFilePath}`);

    const writer = fs.createWriteStream(tempFilePath);

    try {
        const response = await axios({
            method: 'get',
            url: videoUrl,
            responseType: 'stream',
            timeout: config.downloadTimeout, // Set timeout
        });

        // Check status code
        if (response.status < 200 || response.status >= 300) {
            throw new Error(`Server responded with status code ${response.status}`);
        }

        // Pipe the stream to the file
        response.data.pipe(writer);

        return new Promise((resolve, reject) => {
            writer.on('finish', () => {
                console.log(`Successfully downloaded video to ${tempFilePath}`);
                resolve(tempFilePath);
            });
            writer.on('error', (err) => {
                console.error(`Error writing downloaded file: ${err.message}`);
                fs.remove(tempFilePath).catch(e => console.error(`Failed to remove partial download: ${e.message}`)); // Cleanup partial file
                reject(new Error(`Failed to write video file: ${err.message}`));
            });
            // Handle potential timeout during download stream
             response.data.on('error', (err) => {
                 console.error(`Error during download stream: ${err.message}`);
                 writer.close();
                 fs.remove(tempFilePath).catch(e => console.error(`Failed to remove partial download on stream error: ${e.message}`));
                 reject(new Error(`Download stream error: ${err.message}`));
             });
        });
    } catch (error) {
        console.error(`Failed to download video from ${videoUrl}: ${error.message}`);
        // Attempt cleanup if writer was created
        if (writer && !writer.closed) {
             writer.close();
        }
        await fs.remove(tempFilePath).catch(e => console.error(`Failed to remove partial download on error: ${e.message}`));
        // Re-throw a more specific error for the controller
        if (axios.isAxiosError(error)) {
             if (error.response) {
                 throw new Error(`Download failed: Server responded with status ${error.response.status}`);
             } else if (error.request) {
                 throw new Error('Download failed: No response received from server.');
             } else {
                  throw new Error(`Download failed: ${error.message}`);
             }
         } else {
            throw new Error(`Download failed: ${error.message}`);
         }
    }
};


export { getTempAudioPath, cleanupFiles, downloadVideoFromUrl };
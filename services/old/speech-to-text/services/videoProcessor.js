// services/videoProcessor.js
import ffmpeg from 'fluent-ffmpeg';
import path from 'path';
import fs from 'fs-extra'; // Use fs-extra for ensureDir and promises
import Groq from 'groq-sdk/index.mjs';
import config from '../config/index.js';

// Helper to get path for the initial full audio extraction
const getFullAudioPath = (baseFilename, extension = 'mp3') => {
    const stem = path.parse(baseFilename).name;
    // Use a slightly different name to distinguish from potential chunks later
    return path.join(config.tempDir, `${stem}_full_audio.${extension}`);
};

// Initialize Groq client
const groq = new Groq({
    apiKey: config.groqApiKey,
});

// Extract the *full* audio initially (can use compression from Option 1 if desired)
const extractAudio = (videoPath) => {
    return new Promise((resolve, reject) => {
        const audioPath = getFullAudioPath(videoPath, 'mp3'); // Extract as mp3 initially
        console.log(`Extracting full audio from ${videoPath} to ${audioPath}...`);

        ffmpeg(videoPath)
            .noVideo()
            .audioCodec('libmp3lame')
            .audioBitrate('128k') // Moderate bitrate, adjust if needed
            .output(audioPath)
            .on('end', () => {
                console.log(`Full audio extraction finished: ${audioPath}`);
                resolve(audioPath);
            })
            .on('error', (err) => {
                console.error(`Error during full audio extraction: ${err.message}`);
                reject(new Error(`ffmpeg error: ${err.message}`));
            })
            .run();
    });
};


// --- NEW: Function to split audio into chunks ---
const splitAudio = (fullAudioPath, taskId) => {
    return new Promise(async (resolve, reject) => {
        const chunkDir = path.join(config.tempDir, `${taskId}_chunks`);
        const chunkPattern = path.join(chunkDir, `chunk_%03d.mp3`); // Output chunks as mp3
        const segmentTimeSeconds = 590; // Target ~9.8 minutes per chunk (safer than 600 for 25MB limit)

        try {
            await fs.ensureDir(chunkDir); // Create directory for chunks
            console.log(`Splitting audio ${fullAudioPath} into chunks in ${chunkDir}...`);

            ffmpeg(fullAudioPath)
                .outputOptions([
                    '-f segment',             // Use segment muxer
                    `-segment_time ${segmentTimeSeconds}`, // Split time
                    '-c copy',                // Copy codec (fast, assumes source is ok for Groq)
                    '-reset_timestamps 1',    // Reset timestamps for each chunk
                ])
                .output(chunkPattern)
                .on('end', async () => {
                    console.log(`Audio splitting finished.`);
                    // List the created chunk files
                    const files = await fs.readdir(chunkDir);
                    const chunkPaths = files
                        .filter(file => file.startsWith('chunk_') && file.endsWith('.mp3'))
                        .map(file => path.join(chunkDir, file))
                        .sort(); // Ensure chunks are processed in order
                    console.log(`Generated ${chunkPaths.length} audio chunks.`);
                    if (chunkPaths.length === 0) {
                        console.warn("Splitting resulted in zero chunk files. Original file might be too short or an error occurred silently.");
                        // If the original was likely small enough, maybe just return it? Or fail.
                        // For now, let's try returning the original if no chunks produced
                        const stats = await fs.stat(fullAudioPath);
                        if (stats.size < 25 * 1024 * 1024) { // Check if original is under limit
                             console.log("Original file seems small enough, using it directly.");
                             resolve([fullAudioPath]); // Return original path in an array
                             return;
                        } else {
                             reject(new Error("Audio splitting failed to produce chunk files for a large input."));
                             return;
                        }

                    }
                    resolve(chunkPaths);
                })
                .on('error', (err) => {
                    console.error(`Error during audio splitting: ${err.message}`);
                    reject(new Error(`ffmpeg splitting error: ${err.message}`));
                })
                .run();
        } catch (error) {
             console.error(`Error setting up audio splitting: ${error.message}`);
             reject(error);
        }
    });
};


// --- MODIFIED: Transcribe audio chunks ---
const transcribeAudio = async (audioChunkPaths) => {
    console.log(`Starting transcription for ${audioChunkPaths.length} audio chunks using Groq...`);

    if (!config.groqApiKey) {
        console.error("Groq API Key is missing. Cannot transcribe.");
        throw new Error("Transcription failed: Groq API Key is not configured.");
    }

    let combinedTranscript = "";
    let chunkIndex = 0;

    for (const chunkPath of audioChunkPaths) {
        chunkIndex++;
        console.log(`Transcribing chunk ${chunkIndex}/${audioChunkPaths.length}: ${path.basename(chunkPath)}`);
        try {
             // Check chunk size before sending (optional but good practice)
             const stats = await fs.stat(chunkPath);
             if (stats.size >= 25 * 1024 * 1024) {
                 console.warn(`Skipping chunk ${chunkIndex} as its size (${(stats.size / (1024*1024)).toFixed(1)} MB) meets or exceeds the 25MB limit.`);
                 continue; // Skip this chunk
             }
             if (stats.size === 0) {
                 console.warn(`Skipping chunk ${chunkIndex} as it has zero size.`);
                 continue; // Skip empty chunk
             }


            const transcription = await groq.audio.transcriptions.create({
                file: fs.createReadStream(chunkPath),
                model: "whisper-large-v3",
            });

            if (transcription && transcription.text) {
                combinedTranscript += transcription.text + " "; // Add space between chunks
            } else {
                 console.warn(`Groq transcription response for chunk ${chunkIndex} did not contain text.`);
            }
            console.log(`Chunk ${chunkIndex} transcribed successfully.`);

        } catch (error) {
            console.error(`Groq transcription failed for chunk ${chunkIndex} (${path.basename(chunkPath)}): ${error.message}`);
            // Option: Decide whether to fail the whole task or just skip the chunk
            // For now, let's log the error and continue, the final transcript will be incomplete
             if (error instanceof Groq.APIError) {
                 console.error("Groq API Error Details:", { status: error.status, error: error.error });
             }
             // If you want to fail the whole task on a single chunk error, uncomment the next line:
             // throw new Error(`Transcription failed on chunk ${chunkIndex}: ${error.message}`);
        }
    }

    console.log('Combined transcription finished.');
    return combinedTranscript.trim(); // Return combined text, removing trailing space
};

// --- NEW: Helper function to clean up chunk directory ---
const cleanupChunks = async (taskId) => {
     const chunkDir = path.join(config.tempDir, `${taskId}_chunks`);
     try {
         const exists = await fs.pathExists(chunkDir);
         if (exists) {
             await fs.remove(chunkDir);
             console.log(`Cleaned up chunk directory: ${chunkDir}`);
         }
     } catch (error) {
         console.error(`Error cleaning up chunk directory ${chunkDir}: ${error.message}`);
     }
 };


export { extractAudio, splitAudio, transcribeAudio, cleanupChunks }; // Export new functions
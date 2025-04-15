// controllers/taskController.js
import Task from '../models/Task.js';
import { downloadVideoFromUrl, cleanupFiles as cleanupSingleFiles } from '../utils/fileHandler.js'; // Renamed for clarity
import { extractAudio, splitAudio, transcribeAudio, cleanupChunks } from '../services/videoProcessor.js'; // Import new functions
import path from 'path';

// --- Background Task Processing (Modified for Chunking) ---
const processVideoTask = async (taskId, videoUrl) => {
    console.log(`[Task:${taskId}] Starting background processing for URL: ${videoUrl}`);
    let task;
    let tempVideoPath = null;
    let tempFullPath = null; // Path for the initial full audio extraction
    let audioChunkPaths = []; // Array to hold paths of audio chunks

    try {
        // 1. Update status: DOWNLOADING
        task = await Task.findByIdAndUpdate(taskId, { status: 'DOWNLOADING' }, { new: true });
        if (!task) throw new Error('Task not found after initial update.');

        tempVideoPath = await downloadVideoFromUrl(videoUrl, taskId);
        console.log(`[Task:${taskId}] Video downloaded to ${tempVideoPath}`);

        // 2. Update status: EXTRACTING_AUDIO (Full)
        task = await Task.findByIdAndUpdate(taskId, { status: 'EXTRACTING_AUDIO' }, { new: true });
        if (!task) throw new Error('Task not found before audio extraction.');

        tempFullPath = await extractAudio(tempVideoPath); // Extract full audio first
        console.log(`[Task:${taskId}] Full audio extracted to ${tempFullPath}`);

        // 3. Split Audio into Chunks
        // (No specific status for splitting, could add one if needed)
        console.log(`[Task:${taskId}] Splitting audio into chunks...`);
        audioChunkPaths = await splitAudio(tempFullPath, taskId); // Split the extracted audio
        console.log(`[Task:${taskId}] Audio split into ${audioChunkPaths.length} chunks.`);

        // 4. Update status: TRANSCRIBING (Chunks)
        task = await Task.findByIdAndUpdate(taskId, { status: 'TRANSCRIBING' }, { new: true });
        if (!task) throw new Error('Task not found before transcription.');

        const transcript = await transcribeAudio(audioChunkPaths); // Transcribe the chunks
         if (transcript === null || transcript === undefined) {
             // Handle cases where transcription might return empty/null even without errors
             console.warn(`[Task:${taskId}] Transcription resulted in null or empty result.`);
             // Optional: Treat empty transcript as failure or success based on requirements
              throw new Error("Transcription resulted in empty text.");
         }
        console.log(`[Task:${taskId}] Transcription successful.`);

        // 5. Update status: DONE and store result
        task = await Task.findByIdAndUpdate(
            taskId,
            {
                status: 'DONE',
                transcript: transcript,
                errorMessage: null // Clear previous errors
            },
            { new: true }
        );
        if (!task) throw new Error('Task not found when saving final result.');
        console.log(`[Task:${taskId}] Task completed successfully.`);

    } catch (error) {
        const errorMsg = `Task failed: ${error.message}`;
        console.error(`[Task:${taskId}] ${errorMsg}`, error.stack); // Log stack for better debugging
        try {
            // Update status to FAILED with error message
            await Task.findByIdAndUpdate(taskId, { status: 'FAILED', errorMessage: errorMsg });
        } catch (dbError) {
            console.error(`[Task:${taskId}] CRITICAL: Failed to update task status to FAILED: ${dbError.message}`);
        }
    } finally {
        // 6. Cleanup temporary files ALWAYS
        console.log(`[Task:${taskId}] Cleaning up temporary files...`);
        // Clean up original video and full audio extract
        await cleanupSingleFiles(tempVideoPath, tempFullPath);
        // Clean up the directory containing audio chunks
        await cleanupChunks(taskId); // Use the new chunk cleanup function
        console.log(`[Task:${taskId}] Background processing finished.`);
    }
};

// --- API Endpoint Handlers (submitTask, getTaskStatus, getTaskResult) ---
// Keep these functions exactly the same as in the previous version.
// POST /api/tasks - Submit a new task
const submitTask = async (req, res) => {
    const { videoUrl } = req.body;

    if (!videoUrl) {
        return res.status(400).json({ message: 'Missing videoUrl in request body' });
    }

    try {
        // Validate URL format (basic)
        new URL(videoUrl);
    } catch (error) {
         return res.status(400).json({ message: 'Invalid videoUrl format' });
    }


    try {
        const newTask = new Task({ videoUrl }); // Mongoose assigns _id (which is our taskId)
        await newTask.save();

        console.log(`Created task ${newTask._id} for URL ${videoUrl}`);

        // Start background processing - DO NOT await this
        processVideoTask(newTask._id, videoUrl);

        // Respond immediately with 202 Accepted
        res.status(202).json({ taskId: newTask._id });

    } catch (error) {
        console.error(`Failed to submit task for URL ${videoUrl}: ${error.message}`);
        res.status(500).json({ message: 'Failed to create processing task.' });
    }
};

// GET /api/tasks/:taskId/status - Get task status
const getTaskStatus = async (req, res) => {
    try {
        const task = await Task.findById(req.params.taskId).select('status updatedAt'); // Select only needed fields

        if (!task) {
            return res.status(404).json({ message: 'Task not found' });
        }

        res.status(200).json({
            taskId: task._id,
            status: task.status,
            updatedAt: task.updatedAt,
        });
    } catch (error) {
         // Handle potential invalid UUID format for ID
         if (error.name === 'CastError' && error.path === '_id') {
            return res.status(400).json({ message: 'Invalid Task ID format' });
         }
        console.error(`Error fetching status for task ${req.params.taskId}: ${error.message}`);
        res.status(500).json({ message: 'Error retrieving task status.' });
    }
};

// GET /api/tasks/:taskId/result - Get full task result
const getTaskResult = async (req, res) => {
     try {
        const task = await Task.findById(req.params.taskId);

        if (!task) {
            return res.status(404).json({ message: 'Task not found' });
        }

        // Return the full task document structure
        res.status(200).json({
             taskId: task._id,
             status: task.status,
             videoUrl: task.videoUrl,
             transcript: task.transcript, // Will be null if not DONE or if failed before transcription
             error: task.errorMessage, // Will be null if successful
             createdAt: task.createdAt,
             updatedAt: task.updatedAt
         });
    } catch (error) {
        // Handle potential invalid UUID format for ID
        if (error.name === 'CastError' && error.path === '_id') {
            return res.status(400).json({ message: 'Invalid Task ID format' });
        }
        console.error(`Error fetching result for task ${req.params.taskId}: ${error.message}`);
        res.status(500).json({ message: 'Error retrieving task result.' });
    }
};


export { submitTask, getTaskStatus, getTaskResult }; // Ensure correct exports
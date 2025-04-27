// routes/tasks.js
import express from 'express';
import { submitTask, getTaskStatus, getTaskResult } from '../controllers/taskController.js';

const router = express.Router();

// POST /api/tasks - Submit a video URL for processing
router.post('/', submitTask);

// GET /api/tasks/:taskId/status - Check the status of a task
router.get('/:taskId/status', getTaskStatus);

// GET /api/tasks/:taskId/result - Get the final result (transcript or error)
router.get('/:taskId/result', getTaskResult);


export default router;
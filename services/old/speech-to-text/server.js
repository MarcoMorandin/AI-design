// server.js
import express from 'express';
import config from './config/index.js';
import connectDB from './config/db.js';
import taskRoutes from './routes/tasks.js';

// Connect to Database
connectDB();

const app = express();

// Middleware to parse JSON bodies
app.use(express.json());

// --- API Routes ---
app.use('/api/tasks', taskRoutes);

// --- Basic Root Route ---
app.get('/', (req, res) => {
    res.send(`
        <h1>NodeJS Video Transcriber API</h1>
        <p>Use POST /api/tasks to submit a job.</p>
        <p>Check status with GET /api/tasks/{taskId}/status.</p>
        <p>Get results with GET /api/tasks/{taskId}/result.</p>
    `);
});


// --- Start Server ---
const PORT = config.port;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Temporary files stored in: ${config.tempDir}`);
});

// Optional: Graceful shutdown
process.on('SIGINT', async () => {
  console.log('SIGINT signal received: closing MongoDB connection and exiting.');
  await mongoose.connection.close(); // Ensure mongoose is imported or handle differently
  process.exit(0);
});
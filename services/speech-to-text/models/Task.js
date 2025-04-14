// models/Task.js
import mongoose from 'mongoose';
import { v4 as uuidv4 } from 'uuid';

const taskSchema = new mongoose.Schema({
    _id: { 
        type: String,
        default: uuidv4,
    },
    url: {
        type: String,
        required: true,
    },
    status: {
        type: String,
        enum: [
            'PENDING',
            'DOWNLOADING',
            'EXTRACTING_AUDIO',
            'TRANSCRIBING',
            'DONE',
            'FAILED',
        ],
        default: 'PENDING',
    },
    text: {
        type: String,
        default: null,
    },
    errorMessage: {
        type: String,
        default: null,
    },
    createdAt: {
        type: Date,
        default: Date.now,
    },
    updatedAt: {
        type: Date,
        default: Date.now,
    },
});

// Middleware to update `updatedAt` field on save
taskSchema.pre('save', function (next) {
    this.updatedAt = Date.now();
    next();
});

// Middleware to update `updatedAt` field on findOneAndUpdate
taskSchema.pre('findOneAndUpdate', function (next) {
    this.set({ updatedAt: new Date() });
    next();
});


const Task = mongoose.model('Task', taskSchema);

export default Task;
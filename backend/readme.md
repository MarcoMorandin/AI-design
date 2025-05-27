# Drive Authenticator RESTful API

This service provides a RESTful backend for Google Drive authentication and file management. It's designed to be called from a frontend application built in React or Vue.js.

## Running the Service

To run the service:

1. Activate your virtual environment:
   ```
   source .venv/bin/activate   # On macOS/Linux
   ```

2. From the AI-design folder, run:
   ```
   uvicorn drive-authenticator.main:app --reload --port 3000
   ```

## API Endpoints

### Authentication Endpoints

- **GET /api/auth/google**: Initiates the Google OAuth flow 
- **GET /api/auth/google/callback**: OAuth callback from Google 
- **POST /api/auth/token**: Generate a new JWT access token
- **POST /api/auth/refresh**: Refresh an existing JWT token
- **GET /api/auth/logout**: Logout and clear session

### User Endpoints

- **GET /api/user/profile**: Get the current user's profile
- **GET /api/user/folders**: Get the user's Google Drive folder structure
- **GET /api/user/courses**: Get the list of courses (top-level folders)
- **GET /api/user/courses/{course_id}**: Get a specific course folder structure

### Orchestrator Endpoints

- **POST /api/orchestrator/message**: Send a message to the orchestrator agent

## Authentication Flow

1. Frontend redirects the user to `/api/auth/google`
2. User signs in with Google and grants permissions
3. Google redirects back to `/api/auth/google/callback`
4. Service creates/updates the user in the database, creates a Google Drive folder if needed
5. Service issues a JWT token and redirects to the frontend with the token
6. Frontend stores the token and uses it for all subsequent API calls

## Using the API from Frontend

### React Example

```javascript
// Example using axios in React
import axios from 'axios';

const API_URL = 'http://localhost:3000';
let token = localStorage.getItem('auth_token');

// Setup axios with authentication headers
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Get user profile
async function getUserProfile() {
  try {
    const response = await api.get('/api/user/profile');
    return response.data;
  } catch (error) {
    console.error('Error fetching profile:', error);
  }
}

// Get user courses
async function getUserCourses() {
  try {
    const response = await api.get('/api/user/courses');
    return response.data.courses;
  } catch (error) {
    console.error('Error fetching courses:', error);
  }
}

// Send message to orchestrator
async function sendOrchestrator(message, sessionId) {
  try {
    const response = await api.post('/api/orchestrator/message', {
      message: message,
      session_id: sessionId,
      user_id: 'current_user_id'
    });
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);
  }
}
```

### Vue.js Example

```javascript
// Example using axios in Vue.js
import axios from 'axios';

const API_URL = 'http://localhost:3000';
let token = localStorage.getItem('auth_token');

// Create axios instance with auth header
const api = axios.create({
  baseURL: API_URL,
});

// Add auth token to every request
api.interceptors.request.use(config => {
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

export default {
  // Get user profile
  getUserProfile() {
    return api.get('/api/user/profile');
  },
  
  // Get user courses
  getUserCourses() {
    return api.get('/api/user/courses');
  },
  
  // Get course content
  getCourseContent(courseId) {
    return api.get(`/api/user/courses/${courseId}`);
  },
  
  // Send message to orchestrator
  sendOrchestratorMessage(message, sessionId, userId) {
    return api.post('/api/orchestrator/message', {
      message,
      session_id: sessionId,
      user_id: userId
    });
  }
};
```

## Environment Variables

Create a `.env` file with the following variables:

```
ENVIRONMENT=development
FLASK_SECRET_KEY=your_secret_key
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=driveauth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
BASE_URL=http://localhost:3000
FRONTEND_URL=http://localhost:5173  # or your frontend URL
ORCHESTRATOR_URL=https://ai-design-orchestrator-595073969012.europe-west1.run.app
```
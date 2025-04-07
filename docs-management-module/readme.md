# Multi-User Google Drive API Server

This Node.js application provides a RESTful API server allowing multiple users to:

1.  Authenticate with the application using their Google Account (Google Sign-In).
2.  Authorize the application to access their Google Drive.
3.  Automatically have a dedicated folder (`moodleAI_<userGoogleId>`) created or looked up within their Google Drive.
4.  Retrieve the folder tree structure of their dedicated Drive folder via a secure API endpoint.

It uses Express.js, Passport.js for authentication, Mongoose for MongoDB interaction, Google APIs Client Library, and JWT for securing API endpoints. User refresh tokens for Google Drive access are encrypted at rest in the database.


## Installation

1.  **Clone the Repository (or get the code):**

2.  **Install Dependencies:**
    ```bash
    npm install
    ```
    This will install Express, Mongoose, Passport, Google APIs, JWT, dotenv, and other necessary packages listed in `package.json`.

## Configuration

This application requires several environment variables for credentials and secrets.

1.  **Google Cloud Project Setup:**
    * Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
    * Select or create a Google Cloud Project.
    * Go to **APIs & Services -> Enabled APIs & services**. Click **+ ENABLE APIS AND SERVICES**. Search for and enable:
        * **Google Drive API**
        * **Google People API** (Used by Passport for profile info during login)
    * Go to **APIs & Services -> Credentials**.
    * Click **Configure Consent Screen**:
        * Choose **External** (usually appropriate for development/testing). Click **Create**.
        * Fill in the required app name, user support email, and developer contact information.
        * **Scopes:** Click **Add or Remove Scopes**. Add the following scopes:
            * `.../auth/userinfo.email` (for email)
            * `.../auth/userinfo.profile` (for name/profile info)
            * `.../auth/drive` (for Google Drive access)
        * Click **Update**. Save and continue.
        * **Test users:** Add the Google Account(s) you will use for testing if your app is in "testing" mode. Save and continue.
    * Go back to the **Credentials** tab. Click **+ CREATE CREDENTIALS -> OAuth client ID**.
    * **Application type:** Select **Web application**.
    * **Name:** Give your credential a name (e.g., "Web App Drive Integration").
    * **Authorized JavaScript origins:** Add `http://localhost:3000` (Adjust the port if you change it in the code/`.env`).
    * **Authorized redirect URIs:** Add **BOTH** of the following:
        * `http://localhost:3000/auth/google/callback`
        * `http://localhost:3000/connect/drive/callback`
    * Click **Create**.
    * A pop-up will show your **Client ID** and **Client Secret**. **Copy these values immediately.** You'll need them for the `.env` file.

2.  **Create `.env` File:**
    * In the root directory of your project, create a file named `.env`.

3.  **Populate `.env` File:**
    * Paste the following content into your `.env` file and replace the placeholder values:

    ```dotenv
    # Google OAuth Credentials (from Cloud Console)
    GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET

    # MongoDB Connection String (replace with your actual connection string)
    MONGO_URI=mongodb://localhost:27017/multi_user_drive_app

    # Session Secret (generate a long, random string)
    SESSION_SECRET= # Paste output from: openssl rand -base64 32

    # Encryption Key for Drive Tokens (MUST be a 32-byte key, base64 encoded)
    ENCRYPTION_KEY= # Paste output from: openssl rand -base64 32

    # JWT Secret (generate a long, random, secure string)
    JWT_SECRET= # Paste output from: openssl rand -base64 32 (or longer)

    # Base URL of your running application
    BASE_URL=http://localhost:3000
    ```

    * **Generate Secrets:** Open your terminal and run the following commands one by one, pasting the output into the corresponding variable in the `.env` file:
        ```bash
        # For SESSION_SECRET
        openssl rand -base64 32

        # For ENCRYPTION_KEY (Ensure this exact command is used for 32-bytes)
        openssl rand -base64 32

        # For JWT_SECRET
        openssl rand -base64 32
        ```
        *(Alternatively, use `node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"` for each)*

    * **Save** the `.env` file. **Never commit this file to Git.**

## Running the Application

1.  **Start MongoDB:** Ensure your MongoDB instance is running and accessible via the `MONGO_URI` you provided.
2.  **Start the Node.js Server:** Open your terminal in the project's root directory and run:
    ```bash
    # Make sure your script filename matches (e.g., server.js or restful.js)
    node server.js
    ```
3.  You should see console output indicating:
    * `MongoDB Connected`
    * `Server running at http://localhost:3000`

## Usage / API Flow

1.  **Login to the Application:**
    * Open your web browser and navigate to `http://localhost:3000`.
    * Click the "Login with Google" link.
    * You will be redirected to Google. Sign in with a Google account you added as a test user (if required by your consent screen setup). Grant permission for profile/email access.

2.  **Get JWT (Demonstration Method):**
    * Upon successful login, you'll be redirected back to `http://localhost:3000/?token=...`.
    * The page will display the received JWT in an input box. **Copy this token value.**
    * **SECURITY WARNING:** This method of displaying the token in the URL/page is **insecure** and for demonstration only. In a real application, a frontend framework (React, Vue, etc.) would securely receive and store this token (e.g., in memory, localStorage) without exposing it in the URL.

3.  **Link Google Drive:**
    * On the homepage (`http://localhost:3000`), click the "Link Google Drive" link (this only appears if Drive is not yet linked).
    * You will be redirected to Google again. Grant permission for the application to access your Google Drive (`.../auth/drive` scope).
    * Upon success, you'll be redirected back to the homepage. The status should now show Drive as linked, and a folder named `moodleAI_<yourGoogleId>` should exist in the root of your Google Drive.

4.  **Access the API Endpoint:**
    * The primary API endpoint is `GET /api/drive/tree`.
    * You need to send your JWT in the `Authorization` header.
    * **Using `curl`:**
        ```bash
        # Replace YOUR_COPIED_JWT_TOKEN with the actual token
        curl -H "Authorization: Bearer YOUR_COPIED_JWT_TOKEN" http://localhost:3000/api/drive/tree
        ```
    * **Using Postman / Insomnia:**
        * Create a new `GET` request to `http://localhost:3000/api/drive/tree`.
        * Go to the "Authorization" tab.
        * Select Type: "Bearer Token".
        * Paste your copied JWT into the "Token" field.
        * Send the request.
    * **Using the Demo Button:** The homepage includes a basic button ("View Drive Folder Tree (via API)") that prompts for the token and uses the browser's `Workspace` API. Check the browser's console for the JSON output.
    * **Expected Response:** A JSON object containing the folder tree structure of your dedicated `moodleAI_...` folder.
        ```json
        {
          "success": true,
          "tree": {
            "id": "YOUR_DRIVE_FOLDER_ID",
            "name": "moodleAI_YOUR_GOOGLE_ID",
            "type": "folder",
            "children": [
              // ... contents of the folder (files and subfolders) ...
            ]
          }
        }
 
4.  **Upload file:**       ```
    * **Using Postman / Insomnia:**
        * Create a new `POST` request to `http://localhost:3000/api/documents/upload`.
        * Go to the "Authorization" tab.
        * Select Type: "Bearer Token".
        * Paste your copied JWT into the "Token" field.
        * Go to the "Body" tab.
        * Select "form-data" as the type.
        * Add new field named "folderName" (default is the root folder).
        * Add a new field named "file" and select "File" as the type.
        * Click "Select Files" and choose the file you want to upload.
        * Send the request.
6.  **Logout:**
    * Visit `http://localhost:3000/auth/logout` in your browser to clear your application session.

## Security Notes

* **Production Environment:** This code is an example and requires significant hardening for production.
* **Secret Management:** **NEVER** commit your `.env` file to version control (add it to `.gitignore`). Use secure secret management solutions (like HashiCorp Vault, AWS Secrets Manager, Google Secret Manager, or environment variables injected securely by your deployment platform) in production.
* **Token Handling:** The demo method of passing the JWT via URL query parameter is **INSECURE**. Implement a secure frontend flow to handle token reception and storage (e.g., using HttpOnly cookies managed by the backend or secure storage mechanisms in your frontend framework, being mindful of XSS risks with localStorage).
* **Encryption Keys:** Protect your `ENCRYPTION_KEY` rigorously. Key rotation policies should be considered for production.
* **HTTPS:** Always use HTTPS in production to protect data in transit.
* **Input Validation & Rate Limiting:** Add input validation and rate limiting to API endpoints.
* **Error Handling:** Implement more robust error handling and avoid leaking sensitive stack traces in production responses.

## License

Please add a license file (e.g., MIT License) if distributing this code.
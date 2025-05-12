const { google } = require("googleapis");
const User = require("../models/User");
const { encrypt } = require("../utils/encryption");
require("dotenv").config();

const GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"];
const TARGET_FOLDER_BASE_NAME = "moodleAI";


// Find or create the user's specific folder in THEIR Drive
async function getOrCreateUserDriveFolder(drive, user) {
    const folderName = `${TARGET_FOLDER_BASE_NAME}_${user.googleId}`; // Unique folder name per user
    try {
        console.log(`Searching for user folder: ${folderName} for user ${user.id}`);
        const searchRes = await drive.files.list({
            q: `mimeType='application/vnd.google-apps.folder' and name='${folderName}' and trashed=false and 'me' in owners`, // Search only user's owned folders
            fields: 'files(id, name)',
            spaces: 'drive',
            pageSize: 1
        });

        if (searchRes.data.files && searchRes.data.files.length > 0) {
            const existingFolder = searchRes.data.files[0];
            console.log(`User folder '${existingFolder.name}' found with ID: ${existingFolder.id}`);
            return { folderId: existingFolder.id, folderName: existingFolder.name };
        } else {
            console.log(`User folder '${folderName}' not found. Creating...`);
            const createRes = await drive.files.create({
                requestBody: {
                    name: folderName,
                    mimeType: 'application/vnd.google-apps.folder',
                },
                fields: 'id, name',
            });
            const newFolder = createRes.data;
            console.log(`User folder '${newFolder.name}' created with ID: ${newFolder.id}`);
            return { folderId: newFolder.id, folderName: newFolder.name };
        }
    } catch (error) {
        console.error(`Error searching/creating user folder '${folderName}' for user ${user.id}:`, error.response ? error.response.data : error.message);
        throw new Error(`Failed to get or create user Drive folder '${folderName}'.`);
    }
}

exports.driveLink = (req, res) => {
    // Initiate Google Drive linking for the already logged-in user
    const oAuth2Client = new google.auth.OAuth2(
        process.env.GOOGLE_CLIENT_ID,
        process.env.GOOGLE_CLIENT_SECRET,
        `${process.env.BASE_URL}/connect/drive/callback` // Use the specific Drive callback
    );

    const authUrl = oAuth2Client.generateAuthUrl({
        access_type: 'offline', // Request refresh token
        scope: GOOGLE_DRIVE_SCOPES,
        prompt: 'consent', // Force consent screen to ensure refresh token is granted
        state: req.user.id // Pass user's MongoDB ID for tracking in callback
    });
    console.log(`Redirecting user ${req.user.id} to Drive auth URL...`);
    res.redirect(authUrl);
}


exports.driveCallback = async (req, res) => {
   // Handles the redirect back from Google AFTER user grants Drive permission
   const { code, state, error } = req.query;

   // Security Check: Ensure state matches logged-in user ID
   if (error) {
      console.error("Error during Drive OAuth callback:", error);
      return res.status(400).send(`Error during Google Drive authorization: ${error}`);
  }
  if (!state || state !== req.user.id) {
      console.error(`State mismatch during Drive OAuth callback. Expected: ${req.user.id}, Received: ${state}`);
      return res.status(400).send('State parameter mismatch. Potential security issue.');
  }
  if (!code) {
      console.error("Authorization code missing in Drive callback.");
       return res.status(400).send('Authorization code missing.');
  }

  console.log(`Received Drive auth code for user: ${req.user.id}`);

  const oAuth2Client = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      `${process.env.BASE_URL}/connect/drive/callback` // Must match the URI used to generate the auth URL
  );

  try {
      // Exchange the code for tokens
      const { tokens } = await oAuth2Client.getToken(code);
      console.log(`Received Drive tokens for user: ${req.user.id}`);

      // Encrypt the refresh token (if received)
      const encryptedRefreshToken = tokens.refresh_token ? encrypt(tokens.refresh_token) : user.googleTokens?.refresh_token; // Reuse old if not provided
       if (tokens.refresh_token && !encryptedRefreshToken) {
           // Handle critical encryption failure
           throw new Error("Failed to encrypt refresh token during initial linking.");
       }

      // --- Find/Create User's Drive Folder ---
      // Temporarily set credentials on the client to perform Drive actions
      oAuth2Client.setCredentials(tokens);
      const drive = google.drive({ version: 'v3', auth: oAuth2Client });
      const { folderId, folderName } = await getOrCreateUserDriveFolder(drive, req.user);
      // -------------------------------------

      // --- Update User in Database ---
      const updatedUser = await User.findByIdAndUpdate(req.user.id, {
          $set: {
              'googleTokens.access_token': tokens.access_token,
              'googleTokens.refresh_token': encryptedRefreshToken, // Store encrypted version
              'googleTokens.scope': tokens.scope,
              'googleTokens.token_type': tokens.token_type,
              'googleTokens.expiry_date': tokens.expiry_date,
              driveFolderId: folderId,
              driveFolderName: folderName
          }
      }, { new: true }); // Return the updated document

      if (!updatedUser) {
          throw new Error("Failed to find user to update tokens/folder.");
      }
      console.log(`Successfully linked Drive and updated DB for user: ${req.user.id}`);
      // -----------------------------

      res.redirect('/'); // Redirect back to homepage/dashboard

  } catch (err) {
      console.error(`Error exchanging Drive code or updating user ${req.user.id}:`, err.response ? err.response.data : err.message);
      // TODO: Provide better user feedback on error
      res.status(500).send('Failed to link Google Drive account.');
      // Potentially revoke tokens if partially successful but DB update failed?
  } 
}
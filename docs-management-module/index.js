require("dotenv").config();
const express = require("express");
const session = require("express-session");
const passport = require("passport");
const GoogleStrategy = require("passport-google-oauth20").Strategy;
const mongoose = require("mongoose");
const MongoStore = require("connect-mongo");
const { google } = require("googleapis");
const crypto = require("crypto");
const path = require("path");
const jwt = require("jsonwebtoken");

const app = express();
const port = process.env.PORT || 3000;

// --- Configuration ---
const GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"];
const TARGET_FOLDER_BASE_NAME = "moodleAI";
const JWT_EXPIRY = "1d"; // How long JWTs are valid (e.g., 1 day)

// --- Basic Encryption Helpers (Replace with robust solution for production) ---
// WARNING: Key management is crucial and complex. This is a simplified example.
const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 16; // For AES-GCM
const KEY = Buffer.from(process.env.ENCRYPTION_KEY, "base64"); // Ensure ENCRYPTION_KEY is base64 encoded 32 bytes

function encrypt(text) {
  if (!text) return null;
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, KEY, iv);
  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");
  const authTag = cipher.getAuthTag();

  // Store iv and authTag with the encrypted data (e.g., iv:authTag:encrypted)
  return `${iv.toString("hex")}:${authTag.toString("hex")}:${encrypted}`;
}

function decrypt(encryptedText) {
  /* ... as before ... */
  if (!encryptedText) return null;
  try {
    const parts = encryptedText.split(":");
    if (parts.length !== 3) {
      throw new Error("Invalid encrypted text format");
    }
    const [ivHex, authTagHex, encryptedDataHex] = parts;
    const iv = Buffer.from(ivHex, "hex");
    const authTag = Buffer.from(authTagHex, "hex");
    const decipher = crypto.createDecipheriv(ALGORITHM, KEY, iv);
    decipher.setAuthTag(authTag);
    let decrypted = decipher.update(encryptedDataHex, "hex", "utf8");
    decrypted += decipher.final("utf8");
    return decrypted;
  } catch (error) {
    console.error("Decryption failed:", error);
    // Handle decryption errors appropriately - may indicate key mismatch or data corruption
    return null; // Or throw an error depending on desired handling
  }
}

// --- MongoDB Setup ---
mongoose
  .connect(process.env.MONGO_URI)
  .then(() => console.log("MongoDB Connected"))
  .catch((err) => console.error("MongoDB Connection Error:", err));

const UserSchema = new mongoose.Schema({
  googleId: { type: String, required: true, unique: true, index: true }, // Google User ID from profile
  displayName: String,
  email: String,
  googleTokens: {
    // Tokens for accessing THIS USER'S Google Drive
    access_token: String,
    refresh_token: String, // Encrypted
    scope: String,
    token_type: String,
    expiry_date: Number,
  },
  driveFolderId: String, // ID of the user's dedicated folder in their Drive
  driveFolderName: String,
  createdAt: { type: Date, default: Date.now },
});

UserSchema.methods.isDriveLinked = function () {
  return !!this.googleTokens && !!this.googleTokens.access_token;
};
const User = mongoose.model("User", UserSchema);

// --- Passport Setup (Google Sign-In for App Auth) ---
passport.use(
  new GoogleStrategy(
    {
      clientID: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      callbackURL: `${process.env.BASE_URL}/auth/google/callback`,
      scope: ["profile", "email"], // Scopes required for user profile info
    },
    async (accessToken, refreshToken, profile, done) => {
      // This callback handles user login/registration for YOUR APP
      try {
        let user = await User.findOne({ googleId: profile.id });
        if (user) {
          // User exists, log them in
          return done(null, user);
        } else {
          // New user, register them
          const newUser = new User({
            googleId: profile.id,
            displayName: profile.displayName,
            email:
              profile.emails && profile.emails[0]
                ? profile.emails[0].value
                : null,
            // googleTokens and drive fields remain empty until Drive is linked
          });
          await newUser.save();
          return done(null, newUser);
        }
      } catch (err) {
        return done(err, null);
      }
    }
  )
);

passport.serializeUser((user, done) => {
  done(null, user.id); // Store user's MongoDB ID in session
});

passport.deserializeUser(async (id, done) => {
  try {
    const user = await User.findById(id);
    done(null, user); // Attach user object to req.user
  } catch (err) {
    done(err, null);
  }
});

// --- Express Middleware ---
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Session Configuration (Still needed for Passport OAuth flows)
app.use(
  session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    store: MongoStore.create({ mongoUrl: process.env.MONGO_URI }),
    cookie: {
      secure: process.env.NODE_ENV === "production",
      httpOnly: true,
      maxAge: 1000 * 60 * 60 * 24,
    },
  })
);

// Passport Middleware (Initialize Passport and Session support)
app.use(passport.initialize());
app.use(passport.session());

// --- Authentication Middleware ---

// Session-based check (For OAuth initiation/callback flows)
function ensureAuthenticated(req, res, next) {
  if (req.isAuthenticated()) {
    // Checks Passport session
    return next();
  }
  // Redirect to login if session is not valid during OAuth flows
  res.redirect("/auth/google");
}

// JWT-based check (For protecting RESTful API endpoints)
async function verifyJwt(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({
      success: false,
      error: "Unauthorized: Bearer token missing or invalid.",
    });
  }

  const token = authHeader.split(" ")[1];

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);

    // Attach user to request object - Fetch fresh user data from DB
    // This ensures roles/permissions are up-to-date if they change
    const user = await User.findById(decoded.userId);
    if (!user) {
      return res.status(401).json({
        success: false,
        error: "Unauthorized: User not found for token.",
      });
    }

    req.user = user; // Attach the Mongoose user document
    next();
  } catch (err) {
    console.error("JWT Verification Error:", err.name, err.message);
    if (err.name === "TokenExpiredError") {
      return res
        .status(401)
        .json({ success: false, error: "Unauthorized: Token expired." });
    }
    if (err.name === "JsonWebTokenError") {
      return res
        .status(401)
        .json({ success: false, error: "Unauthorized: Invalid token." });
    }
    // Other unexpected errors
    return res.status(500).json({
      success: false,
      error: "Internal server error during token verification.",
    });
  }
}

// --- Google Drive Logic ---

// Helper getDriveClientForUser(user) uses user.googleTokens from DB
async function getDriveClientForUser(user) {
  if (!user || !user.googleTokens || !user.googleTokens.access_token) {
    throw new Error("User Google Drive account is not linked.");
  }

  const oAuth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    `${process.env.BASE_URL}/connect/drive/callback` // Redirect URI used when linking
  );

  const tokens = {
    ...user.googleTokens,
    // IMPORTANT: Decrypt refresh token before setting credentials
    refresh_token: decrypt(user.googleTokens.refresh_token),
  };

  // Check if decryption failed
  if (user.googleTokens.refresh_token && !tokens.refresh_token) {
    console.error(`Failed to decrypt refresh token for user ${user.id}`);
    throw new Error("Failed to prepare Drive credentials. Decryption error.");
  }

  oAuth2Client.setCredentials(tokens);

  oAuth2Client.on("tokens", async (newTokens) => {
    console.log(`Refreshing Drive tokens for user: ${user.id}`);
    
    // IMPORTANT: Update the user's tokens in the database!
    let updatedFields = {
        'googleTokens.access_token': newTokens.access_token,
        'googleTokens.expiry_date': newTokens.expiry_date,
        'googleTokens.scope': newTokens.scope || user.googleTokens.scope, // Keep original scope if not returned
        'googleTokens.token_type': newTokens.token_type || user.googleTokens.token_type,
    };
    
    // Encrypt and update refresh token ONLY if a new one is provided
    if (newTokens.refresh_token) {
      const encryptedRefreshToken = encrypt(newTokens.refresh_token);
      if (!encryptedRefreshToken) {
        console.error(
          `CRITICAL: Failed to encrypt new refresh token for user ${user.id}.`
        );
        // Decide how to handle this critical failure - maybe log and alert
        return; // Avoid saving corrupted state
      }
      updatedFields["googleTokens.refresh_token"] = encryptedRefreshToken;
    } else {
      updatedFields["googleTokens.refresh_token"] =
        user.googleTokens.refresh_token; // Keep existing encrypted one
    }
    try {
      await User.findByIdAndUpdate(user.id, { $set: updatedFields });
      console.log(`Successfully updated tokens in DB for user: ${user.id}`);
        // Update the user object in memory for the current request (optional, depends on flow)
        // Object.assign(user.googleTokens, updatedFields); // Be careful with nested updates
    } catch (dbError) {
      console.error(
        `Error updating refreshed tokens in DB for user ${user.id}:`,
        dbError
      );
        // Handle DB update failure (e.g., retry logic, logging)

    }
  });
  return google.drive({ version: "v3", auth: oAuth2Client });
}

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



// Recursive Tree Function (Needs the user-specific Drive client)
async function getFolderTree(drive, folderId) {
    let children = [];
    let pageToken = null;
    // console.log(` -> Exploring folder ID: ${folderId}`);
    try {
        do {
            const params = {
                q: `'${folderId}' in parents and trashed=false`,
                fields: 'nextPageToken, files(id, name, mimeType)',
                spaces: 'drive',
                pageToken: pageToken,
                pageSize: 200
            };
            const res = await drive.files.list(params);
            const files = res.data.files;

            if (files && files.length > 0) {
                const promises = files.map(async (file) => {
                    if (file.mimeType === 'application/vnd.google-apps.folder') {
                        // console.log(`    Found folder: ${file.name} (${file.id})`);
                        return {
                            id: file.id,
                            name: file.name,
                            type: 'folder',
                            children: await getFolderTree(drive, file.id) // Pass same user-specific drive client
                        };
                    } else {
                        // console.log(`    Found file: ${file.name} (${file.id})`);
                        return {
                            id: file.id,
                            name: file.name,
                            type: 'file',
                            mimeType: file.mimeType
                        };
                    }
                });
                const results = await Promise.all(promises);
                children = children.concat(results);
            }
            pageToken = res.data.nextPageToken;
        } while (pageToken);
        // console.log(` <- Finished exploring folder ID: ${folderId}`);
        return children;
    } catch (error) {
        console.error(`Error listing/processing children of folder ID ${folderId}:`, error.response ? error.response.data : error.message);
        return []; // Return empty on error for this branch
    }
}


// --- Express Routes ---

// Homepage / Status Check (Modified to show token if present in URL)
app.get("/", (req, res) => {
  // WARNING: Displaying token from URL is insecure - for DEMO only!
  const tokenFromUrl = req.query.token;

  if (req.isAuthenticated()) {
    // Check session for basic logged-in status
    let body = `<h1>Welcome, ${req.user.displayName}</h1>`;
    if (tokenFromUrl) {
      body += `<p><b>Received Token (DEMO ONLY - INSECURE):</b> <input type="text" value="${tokenFromUrl}" size="50" readonly></p>
                     <p>Use this token in the 'Authorization: Bearer TOKEN' header for API calls.</p>`;
    } else {
      body += `<p>You are logged in.</p>`;
    }
    body += `<p>Email: ${req.user.email}</p>
                  <p>Drive Linked: ${
                    req.user.isDriveLinked()
                      ? `Yes (Folder: ${req.user.driveFolderName || "N/A"})`
                      : "No"
                  }</p>
                  ${
                    !req.user.isDriveLinked()
                      ? '<a href="/connect/drive">Link Google Drive</a><br>'
                      : ""
                  }
                  ${
                    req.user.isDriveLinked()
                      ? '<a href="#" onclick="fetchTree()">View Drive Folder Tree (via API)</a><br>'
                      : ""
                  }
                  <a href="/auth/logout">Logout</a>

                  <script>
                      async function fetchTree() {
                          const token = prompt("Enter your JWT token (from URL or stored):"); // Simple prompt for demo
                          if (!token) return;
                          try {
                              const response = await fetch('/api/drive/tree', {
                                  headers: { 'Authorization': 'Bearer ' + token }
                              });
                              const data = await response.json();
                              if (response.ok) {
                                  alert('Tree fetched successfully! Check browser console.');
                                  console.log(JSON.stringify(data.tree, null, 2));
                              } else {
                                  alert('Error fetching tree: ' + data.error);
                                  console.error(data);
                              }
                          } catch (err) {
                              alert('Network or fetch error.');
                              console.error(err);
                          }
                      }
                  </script>
                  `;
    res.send(body);
  } else {
    res.send('<h1>Welcome</h1><a href="/auth/google">Login with Google</a>');
  }
});

// == Authentication Routes (App Login - Uses Passport Sessions) ==
app.get(
  "/auth/google",
  passport.authenticate("google", { scope: ["profile", "email"] })
);

app.get(
  "/auth/google/callback",
  passport.authenticate("google", { failureRedirect: "/" }),
  (req, res) => {
    // Successful app authentication via Passport session
    console.log(`User ${req.user.displayName} logged in via session.`);

    // --- Generate JWT ---
    const payload = { userId: req.user.id, googleId: req.user.googleId };
    const token = jwt.sign(payload, process.env.JWT_SECRET, {
      expiresIn: JWT_EXPIRY,
    });
    console.log(`Generated JWT for user: ${req.user.id}`);

    // --- Redirect with Token (INSECURE DEMO METHOD) ---
    // WARNING: Sending tokens in URL is insecure! Use a proper frontend flow in production.
    res.redirect(`/?token=${token}`);
  }
);

app.get('/auth/logout', (req, res, next) => {
    req.logout(function(err) { // req.logout requires a callback
      if (err) { return next(err); }
      req.session.destroy((err) => { // Optional: Destroy session completely
         if (err) {
             console.error("Session destruction error:", err);
         }
         res.clearCookie('connect.sid'); // Clear session cookie
         console.log("User logged out.");
         res.redirect('/');
      });
    });
});

// == Google Drive Linking Routes ==
app.get('/connect/drive', ensureAuthenticated, (req, res) => {
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
});


app.get('/connect/drive/callback', ensureAuthenticated, async (req, res, next) => {
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
});


// == RESTful API Route (Uses JWT Authentication) ==
// Client needs to include 'Authorization: Bearer <JWT_TOKEN>' header
app.get("/api/drive/tree", verifyJwt, async (req, res) => {
  // verifyJwt middleware ensures req.user is populated if token is valid
  try {
    const user = req.user; // User fetched by verifyJwt middleware

    if (!user.isDriveLinked() || !user.driveFolderId) {
      return res.status(400).json({
        success: false,
        error: "Google Drive account not linked or folder not set up.",
      });
    }

    console.log(
      `API: Fetching folder tree for user: ${user.id}, folder: ${user.driveFolderId}`
    );
    const drive = await getDriveClientForUser(user); // Get user-specific Drive client
    const children = await getFolderTree(drive, user.driveFolderId); // Fetch tree

    const tree = {
      id: user.driveFolderId,
      name: user.driveFolderName,
      type: "folder",
      children: children,
    };
    console.log(`API: Successfully retrieved folder tree for user ${user.id}.`);
    res.status(200).json({ success: true, tree: tree }); // Use 200 OK
  } catch (error) {
    console.error(
      `API Error fetching folder tree for user ${req.user?.id}:`,
      error
    );
    // Check for specific errors potentially thrown by getDriveClientForUser or getFolderTree
    if (
      error.message.includes("linked") ||
      error.message.includes("credential") ||
      error.message.includes("decrypt")
    ) {
      res.status(400).json({
        success: false,
        error: `Drive access error: ${error.message}`,
      });
    } else {
      res.status(500).json({
        success: false,
        error: "Internal server error while fetching folder tree.",
      });
    }
  }
});

// --- Server Start ---
app.listen(port, () => {
  console.log(`Server running at ${process.env.BASE_URL}`);
  console.log(
    "Ensure .env file has GOOGLE creds, MONGO_URI, SESSION_SECRET, ENCRYPTION_KEY, JWT_SECRET"
  );
});

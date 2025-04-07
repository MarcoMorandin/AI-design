const express = require("express");
const session = require("express-session");
const MongoStore = require("connect-mongo");
const passport = require("./config/passport");
require('./config/db');
require("dotenv").config();


const app = express();
const port = process.env.PORT || 3000;



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

// --- API Routes ---
const authRoutes = require("./routes/auth");
const driveRoutes = require("./routes/drive");
const apiRoutes = require("./routes/api");

app.use("/auth", authRoutes);
app.use("/connect/drive", driveRoutes);
app.use("/api", apiRoutes);

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


// --- Server Start ---
app.listen(port, () => {
  console.log(`Server running at ${process.env.BASE_URL}`);
  console.log(
    "Ensure .env file has GOOGLE creds, MONGO_URI, SESSION_SECRET, ENCRYPTION_KEY, JWT_SECRET"
  );
});

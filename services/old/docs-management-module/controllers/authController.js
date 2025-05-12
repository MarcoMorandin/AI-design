const jwt = require("jsonwebtoken");
require("dotenv").config();

const JWT_EXPIRY = "1d"; // How long JWTs are valid (e.g., 1 day)


exports.googleCallback=(req,res)=>{
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

exports.logout = (req, res) => {
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
  };
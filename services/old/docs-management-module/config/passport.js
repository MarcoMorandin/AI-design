const passport = require("passport");
const GoogleStrategy = require("passport-google-oauth20").Strategy;
const User = require("../models/User");
require("dotenv").config();


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


module.exports = passport;
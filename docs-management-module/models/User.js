const mongoose = require("mongoose");
require("dotenv").config();


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

// If the user have connected his Drive account
UserSchema.methods.isDriveLinked = function () {
  return !!this.googleTokens && !!this.googleTokens.access_token;
};
const User = mongoose.model("User", UserSchema);
 
module.exports = mongoose.model("User", UserSchema);
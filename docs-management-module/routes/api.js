const express = require("express");
const router = express.Router();
const apiController = require("../controllers/apiController");
const jwt = require("jsonwebtoken");
const User = require("../models/User");
require("dotenv").config();
const multer = require("multer");

const upload = multer({ storage: multer.memoryStorage() });


// Middleware per verificare il JWT
async function verifyJwt(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ success: false, error: "Unauthorized: Bearer token missing or invalid." });
  }
  const token = authHeader.split(" ")[1];
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findById(decoded.userId);
    if (!user) {
      return res.status(401).json({ success: false, error: "Unauthorized: User not found for token." });
    }
    req.user = user;
    next();
  } catch (err) {
    console.error("JWT Verification Error:", err.name, err.message);
    if (err.name === "TokenExpiredError") {
      return res.status(401).json({ success: false, error: "Unauthorized: Token expired." });
    }
    if (err.name === "JsonWebTokenError") {
      return res.status(401).json({ success: false, error: "Unauthorized: Invalid token." });
    }
    return res.status(500).json({ success: false, error: "Internal server error during token verification." });
  }
}
 
router.get("/drive/tree", verifyJwt, apiController.getDriveTree);

router.post("/documents/upload", verifyJwt, upload.single("file"), apiController.uploadDocuments);

router.post("/documents/uploadMd", verifyJwt, upload.single("markdownFile"), apiController.fromMdToDocs);


router.get("/documents/:fileId/getComments", verifyJwt, apiController.getFileComment);

module.exports = router;
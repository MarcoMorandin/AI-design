const express = require("express");
const router = express.Router();
const driveController = require("../controllers/driveController");
require("dotenv").config();


// Middleware per assicurarsi che l'utente sia autenticato
function ensureAuthenticated(req, res, next) {
  if (req.isAuthenticated()) return next();
  res.redirect("/auth/google");
}

router.get("/", ensureAuthenticated, driveController.driveLink);
router.get("/callback", ensureAuthenticated, driveController.driveCallback);

module.exports = router;
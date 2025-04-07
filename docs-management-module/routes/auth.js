const express = require("express");
const passport = require("passport");
const router = express.Router();
const authController = require("../controllers/authController");
require("dotenv").config();


router.get("/google", passport.authenticate("google", { scope: ["profile", "email"] }));

router.get("/google/callback", passport.authenticate("google", { failureRedirect: "/" }), authController.googleCallback);

router.get("/logout", authController.logout);

module.exports = router;
const { google } = require("googleapis");
const User = require("../models/User");
const { decrypt } = require("../utils/encryption");
require("dotenv").config();
const stream = require("stream");
const MarkdownIt = require('markdown-it');

// get Docs API
async function getDocsClientForUser(user) {
  if (!user || !user.googleTokens || !user.googleTokens.access_token) {
    throw new Error("User Google Docs account is not linked.");
  }

  const oAuth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    `${process.env.BASE_URL}/connect/drive/callback`
  );

  const tokens = {
    ...user.googleTokens,
    refresh_token: decrypt(user.googleTokens.refresh_token),
  };

  if (user.googleTokens.refresh_token && !tokens.refresh_token) {
    console.error(`Failed to decrypt refresh token for user ${user.id}`);
    throw new Error("Failed to prepare Docs credentials. Decryption error.");
  }

  oAuth2Client.setCredentials(tokens);

  oAuth2Client.on("tokens", async (newTokens) => {
    console.log(`Refreshing Docs tokens for user: ${user.id}`);
    let updatedFields = {
      'googleTokens.access_token': newTokens.access_token,
      'googleTokens.expiry_date': newTokens.expiry_date,
      'googleTokens.scope': newTokens.scope || user.googleTokens.scope,
      'googleTokens.token_type': newTokens.token_type || user.googleTokens.token_type,
    };

    if (newTokens.refresh_token) {
      const encryptedRefreshToken = encrypt(newTokens.refresh_token);
      if (!encryptedRefreshToken) {
        console.error(`CRITICAL: Failed to encrypt new refresh token for user ${user.id}.`);
        return;
      }
      updatedFields["googleTokens.refresh_token"] = encryptedRefreshToken;
    } else {
      updatedFields["googleTokens.refresh_token"] = user.googleTokens.refresh_token;
    }

    try {
      await User.findByIdAndUpdate(user.id, { $set: updatedFields });
      console.log(`Successfully updated tokens in DB for user: ${user.id}`);
    } catch (dbError) {
      console.error(`Error updating refreshed tokens in DB for user ${user.id}:`, dbError);
    }
  });

  return google.docs({ version: "v1", auth: oAuth2Client });
}


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

async function getFolderIdByName(drive, folderName) {
  try{
    const params={
      q: `name='${folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
      fields: 'files(id, name)',
      spaces: 'drive',
      pageSize: 1
    }
    const res= await drive.files.list(params);
    const files = res.data.files;
    if (files && files.length > 0) {
      return res.data.files[0].id; //return the id
    }else{
      throw new Error('Folder ${folderName} not preesent');
    }
  }catch (error) {
    throw new Error(`Error searching for folder '${folderName}':`, error.response? error.response.data : error.message);
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

exports.getDriveTree=async(req,res)=>{
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
}

// Helper function to upload a base64 image to Google Drive
async function uploadImageToDrive(base64Data, fileName, drive_const) {


  //const folderId= await getFolderIdByName(drive_const, folderName);
  //console.log("folderId", folderId)
  //const drive = await getDriveClientForUser(req.user);
  // Convert base64 to buffer
  const buffer = Buffer.from(base64Data, 'base64');
  
  // Create a readable stream from the buffer
  const bufferStream = new stream.PassThrough();
  bufferStream.end(buffer);
  
  // Upload to Google Drive
  const fileMetadata = {
    name: fileName,
    mimeType: 'image/png'
  };
  
  const media = {
    mimeType: 'image/png',
    body: bufferStream
  };
  
  try {
    const res = await drive_const.files.create({
      resource: fileMetadata,
      media: media,
      fields: 'id'
    });
    
    const fileId = res.data.id;

    // Make the file public
    await drive_const.permissions.create({
      fileId: fileId,
      requestBody: {
        role: 'reader',
        type: 'anyone'
      }
    });

    return fileId;
  } catch (err) {
    console.error('Error uploading image to Drive:', err);
    throw err;
  }
}


exports.uploadMarkdown=async(req,res)=>{
  try {
    console.log(req)
    const { title, text, formulas } = req.body;
    
    if (!title || !text || !formulas) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    const docs = await getDocsClientForUser(req.user);
    const drive=await getDriveClientForUser(req.user);
    // 1. Create a new Google Doc
    //const folderId= await getFolderIdByName(drive_const, req.user.driveFolderName);
    const doc = await docs.documents.create({
      requestBody: {
        title: title
      }
    });
    
    const documentId = doc.data.documentId;


    console.log(`Created new document with ID: ${documentId}`);
    
    // 2. Upload all formula images to Drive
    
    const formulaImageMap = {};
    for (const formula of formulas) {
      if (formula.image_data) {
        const fileId = await uploadImageToDrive(
          formula.image_data, 
          `formula_${formula.placeholder.replace(/[\[\]]/g, '')}`,
          drive
        );
        console.log(fileId)
        formulaImageMap[formula.placeholder] = fileId;
      }
    }
    
    // 3. Process the document text and prepare batch update requests
    const requests = [];

    
    let currentText = text;
    
    // First, insert the entire text
    requests.push({
      insertText: {
        location: { index: 1 },
        text: currentText
      }
    });
    
    // Now, replace all placeholders with images
    let contentLength = currentText.length + 1; // +1 for the initial index
    
    for (const formula of formulas) {
      const { placeholder, type } = formula;
      const fileId = formulaImageMap[placeholder];
      
      if (!fileId) continue;
      
      // Find the position of the placeholder in the text
      const placeholderPos = currentText.indexOf(placeholder);
      if (placeholderPos === -1) continue;
      
      const placeholderIndex = placeholderPos + 1; // +1 for the initial index
      
      // Calculate the placeholder length
      const placeholderLength = placeholder.length;
      
      // Add request to delete the placeholder text
      requests.push({
        deleteContentRange: {
          range: {
            startIndex: placeholderIndex,
            endIndex: placeholderIndex + placeholderLength
          }
        }
      });
      
      // Adjust content length after deletion
      contentLength -= placeholderLength;
      
      // Add request to insert the image at the same position
      requests.push({
        insertInlineImage: {
          location: { index: placeholderIndex },
          uri: `https://drive.google.com/uc?export=view&id=${fileId}`,
          objectSize: {
            height: {
              magnitude: type === 'INLINE_FORMULA' ? 10 : 20,
              unit: 'PT'
            }
          }
        }
      });
      
      // For display formulas, ensure there are newlines before and after
      if (type === 'DISPLAY_FORMULA') {
        // Check if there's already a newline before/after and add if needed
        // This is a simplified approach and might need adjustment
        const textBefore = currentText.substring(0, placeholderPos);
        const textAfter = currentText.substring(placeholderPos + placeholderLength);
        
        if (!textBefore.endsWith('\n')) {
          requests.push({
            insertText: {
              location: { index: placeholderIndex },
              text: '\n'
            }
          });
          contentLength += 1;
        }
        
        if (!textAfter.startsWith('\n')) {
          requests.push({
            insertText: {
              location: { index: placeholderIndex + 1 }, // +1 for the image
              text: '\n'
            }
          });
          contentLength += 1;
        }
      }
      
      // Update the text by removing the processed placeholder
      currentText = 
        currentText.substring(0, placeholderPos) + 
        '█'.repeat(placeholderLength) + // Use a marker to keep the string length the same
        currentText.substring(placeholderPos + placeholderLength);
    }
    
    // 4. Execute the batch update
    if (requests.length > 0) {
      await docs.documents.batchUpdate({
        documentId,
        requestBody: {
          requests
        }
      });
    }
    
    // 5. Return the document ID and URL
    return res.status(200).json({
      success: true,
      documentId,
      documentUrl: `https://docs.google.com/document/d/${documentId}/edit`
    });
    
  } catch (error) {
    //console.error('Error processing document:', error);
    console.error('Error processing document:', error);
    return res.status(500).json({
      success: false,
      error: error.message
    });
  }
};




exports.uploadDocuments=async(req,res)=>{
  try{
    //Default → root folder
    const folderName = req.body.folderName || req.user.driveFolderName;
    if (!folderName){
      return res.status(400).json({
        success: false,
        error: "Invalid request body",
      });
    }
    if (!req.file){
      return res.status(400).json({
        success: false,
        error: "No files uploaded",
      });
    }
    const drive=await getDriveClientForUser(req.user);
    const folderId= await getFolderIdByName(drive, folderName);
    const fileMetadata={
      name: req.file.originalname,
      parents: [folderId],
    };

    const bufferStream = new Readable()
    bufferStream.push(req.file.buffer)
    bufferStream.push(null)

    const media={
      mimeType: req.file.mimetype,
      body: bufferStream,
    }

    const response =await drive.files.create({
      resource: fileMetadata,
      media: media,
      fields: "id, name, mimeType, parents",
    });

    res.status(200).json({
      success: true,
      message: "File uploaded successfully",
      fileId: response.data.id,
    });

  }catch(error){
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
        error: "Internal server error while uploading document.",
      });
    }
  }
}


exports.getFileComment=async(req, res)=>{
  let pageToken=null
  let allComments=[];
  try{
    do{
      const fileId=req.params.fileId;
      if (!fileId){
        return res.status(400).json({
          success: false,
          error: "Invalid request body",
        });
      }
      const drive=await getDriveClientForUser(req.user);
      const response = await drive.comments.list({
        fileId: fileId,
        fields: 'nextPageToken, comments(id,content,createdTime,modifiedTime,author)',
        includeDeleted: False,
        pageToken: pageToken,
        pageSize: 100
      });
      // if more then 100 comments
      if (response.data.comments && response.data.comments.length > 0) {
        allComments = allComments.concat(response.data.comments);
      }
      pageToken = response.data.nextPageToken
    }while(pageToken)
    return res.status(200).json({
      success: true,
      comments: comments,
    });
  }catch (error) {
    console.error("Error fetching file comments:", error.message);
    
    // Handle specific errors
    if (error.message.includes("File not found")) {
      return res.status(404).json({ 
        success: false, 
        error: "File not found or you don't have permission to access it" 
      });
    }
    
    return res.status(500).json({
      success: false,
      error: "Failed to fetch comments from Google Drive",
      details: error.message
    });
  }
}
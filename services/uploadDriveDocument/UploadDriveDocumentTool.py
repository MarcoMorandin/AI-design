import logging


logger = logging.getLogger(__name__)

from .utils.get_formulas import process_document_with_formulas

class UploadDriveDocumentTool:

    def __init__(self, jwt_token, upload_endpoint='http://localhost:3000/api/documents/uploadMarkdown'):
        self.upload_endpoint = upload_endpoint
        self.jwt_token = jwt_token

    def process(self, text, folderName="DEFAULT", doc_name="Document with LaTeX Formulas"):
        result=process_document_with_formulas(text, self.upload_endpoint, self.jwt_token, folderName, doc_name)
        if result==None:
            logger.info("No result from uploading documet")
        else:
            logger.info("Document uploaded correctly")

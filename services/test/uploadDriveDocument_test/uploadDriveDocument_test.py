import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from uploadDriveDocument.UploadDriveDocumentTool import UploadDriveDocumentTool
from get_text import get_text

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():

    jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2ODEwZWMxZjhjYzZiOGY1OWZhMzllZDciLCJnb29nbGVJZCI6IjEwMDE5NzI4OTQ0NzU3MTM5ODY5NSIsImlhdCI6MTc0NTkzOTU2MSwiZXhwIjoxNzQ2MDI1OTYxfQ.PrAMkO_DJYW4Tw4rU8TaSP7MvsCH3ev6VYcSEthhUxE"

    processor=UploadDriveDocumentTool(jwt_token)

    result = processor.process(get_text())


    logger.info("Process complete: ", result)


if __name__ == "__main__":
    # Install the required packages if not already installed (requests)
    main()

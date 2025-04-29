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

    jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2ODA3YTU5YzA2MzVhZjI3MGM1ODY2ZTUiLCJnb29nbGVJZCI6IjEwMDE5NzI4OTQ0NzU3MTM5ODY5NSIsImlhdCI6MTc0NTkyNzkwNCwiZXhwIjoxNzQ2MDE0MzA0fQ.GKLnhf_B6cajnQZF19GyZzAsfm_YcSzL7snoiDQ-in4"

    processor=UploadDriveDocumentTool(jwt_token)

    result = processor.process(get_text())


    logger.info("Process complete: ", result)


if __name__ == "__main__":
    # Install the required packages if not already installed (requests)
    main()

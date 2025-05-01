# UploadDriveDocument Tool

This tool allows you to upload documents (including those with LaTeX formulas) to your Google Drive via the docs-management-module, converting from md to Doc.


## Setup Instructions

### 1. Start the Docs Management Module

1. Navigate to the `docs-management-module` directory.
2. Install dependencies:
    ```bash
    npm install
    ```
3. Start the server:
    ```bash
    npm start
    ```
4. Log in with your Google Drive credentials when prompted.

### 2. Set Up the Python Environment

1. Go to the `uploadDriveDocument` folder inside the `services` directory:
    ```bash
    cd services\uploadDriveDocument
    ```
2. Create a virtual environment:
    ```bash
    python -m venv venv
    ```
3. Activate the virtual environment:
    ```bash
    venv\Scripts\activate
    ```

### 3. Test the UploadDriveDocument Tool

1. Navigate to the test folder:
    ```bash
    cd ..\..\test\uploadDriveDocument
    ```
2. Insert your JWT token into the test script as required.
3. Run the test file:
    ```bash
    python <test_file_name>.py
    ```
    Replace `<test_file_name>.py` with the actual test script filename.

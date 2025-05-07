# AI-design
Github repo for designing large scale AI systems

Please suggest some requirements😁

[Requirements file](https://docs.google.com/document/d/1Rg7ZIygavuiE3DOsFQmwhyblYL-CnRjXOBtcYRM1h5M/edit?usp=sharing)

Here are the architecture

[Architecture file](https://docs.google.com/document/d/1IBGA4AZ8y7XcuF9IBqJkk7Di_eNOdY3P0eH68JhCEXI/edit?usp=sharing)


## Try agent:
([Agent URL](https://ai-design-855231674152.europe-west8.run.app))

### How to try:
- Get Agent Card:

    ```console
    curl -X GET "https://ai-design-855231674152.europe-west8.run.app"
    ```

    ```console
    curl -X GET "https://ai-design-855231674152.europe-west8.run.app/.well-known/agent.json"
    ```

- Create a summarization task:
    ```console
    curl -X POST "https://ai-design-855231674152.europe-west8.run.app/tasks/send" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "'"$(uuidgen | tr -d '\n')"'",
        "params": {
        "id": "'"$(uuidgen | tr -d '\n')"'",
        "sessionId": "'"$(uuidgen | tr -d '\n')"'",
        "message": {
            "role": "user",
            "parts": [
            {
                "type": "text",
                "text": "Summarize this PDF: test.pdf"
            }
            ]
        }
        }
    }'
    ```
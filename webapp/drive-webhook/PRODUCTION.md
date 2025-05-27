# Production Deployment Guide for Drive Webhook

This guide provides instructions for deploying the Drive Webhook service in a production environment.

## Prerequisites

- Docker and Docker Compose installed on your production server
- MongoDB instance (production ready)
- Access to the Google Drive API

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Environment
ENVIRONMENT=production

# MongoDB configuration
MONGO_URI=mongodb://username:password@mongodb-host:27017/
MONGO_DB_NAME=your_database_name

# Service configuration
WEBHOOK_SERVICE_PORT=5001
```

## Deployment Steps

1. Clone the repository on your production server:
   ```bash
   git clone <repository-url>
   cd AI-design
   ```

2. Create the `.env` file with your production settings as described above

3. Deploy using Docker Compose:
   ```bash
   docker-compose up -d drive-webhook
   ```

   Alternatively, to deploy the entire stack:
   ```bash
   docker-compose up -d
   ```

4. Verify the deployment:
   ```bash
   docker-compose ps
   ```

## Monitoring and Maintenance

- Check logs:
  ```bash
  docker-compose logs -f drive-webhook
  ```

- View container status:
  ```bash
  docker ps
  ```

- Update the service:
  ```bash
  git pull
  docker-compose down drive-webhook
  docker-compose up -d --build drive-webhook
  ```

## Security Considerations

1. Always keep MongoDB secure with authentication
2. Implement proper access controls for files being processed
3. Regularly update dependencies and apply security patches

## Integration with Google Drive

Ensure that the webhook service is properly registered with Google Drive to receive notifications about file changes. This typically involves:

1. Setting up Google Drive API notifications
2. Configuring the webhook URL in your Google Cloud Console
3. Setting up proper authentication between Google Drive and your webhook service

## Troubleshooting

If you experience issues with the webhook service:

1. Check that MongoDB is accessible
2. Verify that the service can communicate with Google Drive
3. Check the logs for specific error messages
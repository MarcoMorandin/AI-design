# Production Deployment Guide for Drive Authenticator

This document provides instructions for deploying the Drive Authenticator service in a production environment.

## Prerequisites

- Docker and Docker Compose installed on your production server
- Valid SSL certificates for HTTPS
- MongoDB instance (production ready)
- Google OAuth credentials configured for your production domain

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Environment
ENVIRONMENT=production

# App configuration
FLASK_SECRET_KEY=your_secure_random_secret_key
AUTH_SERVICE_PORT=5000
BASE_URL=https://your-production-domain.com

# MongoDB configuration
MONGO_URI=mongodb://username:password@mongodb-host:27017/
MONGO_DB_NAME=your_database_name

# Google OAuth configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Optional SSL config if not using reverse proxy
SSL_KEYFILE=/app/ssl/key.pem
SSL_CERTFILE=/app/ssl/cert.pem
```

## SSL Configuration

### Option 1: Using a reverse proxy (recommended)

The recommended approach is to use a reverse proxy such as Nginx or Traefik to handle SSL termination.

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-production-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-production-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 2: Direct SSL in the application

If you're not using a reverse proxy, place your SSL certificates in the `./ssl` directory:

```
drive-authenticator/
└── ssl/
    ├── cert.pem
    └── key.pem
```

## Google OAuth Configuration

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Update your OAuth 2.0 Client ID with your production domain
4. Add your production redirect URI: `https://your-production-domain.com/auth/google/callback`

## Deployment Steps

1. Clone the repository on your production server:
   ```bash
   git clone <repository-url>
   cd AI-design
   ```

2. Create the `.env` file with your production settings as described above

3. Deploy using Docker Compose:
   ```bash
   cd drive-authenticator
   docker-compose up -d
   ```

4. Verify the deployment:
   ```bash
   docker-compose ps
   curl -f http://localhost:5000/health
   ```

## Monitoring and Maintenance

- Check logs:
  ```bash
  docker-compose logs -f drive-authenticator
  ```

- View container health status:
  ```bash
  docker ps
  ```

- Update the application:
  ```bash
  git pull
  docker-compose down
  docker-compose up -d --build
  ```

## Security Considerations

1. Ensure `FLASK_SECRET_KEY` is a strong, randomly generated key
2. Always use HTTPS in production
3. MongoDB should be secured with authentication
4. Protect your Google OAuth credentials
5. Consider implementing rate limiting
6. Regularly update dependencies and apply security patches

## Backup Strategy

Regularly backup your MongoDB database to prevent data loss:

```bash
# Example backup command
mongodump --uri="mongodb://username:password@mongodb-host:27017/your_database_name" --out=/path/to/backup/directory
```

## Troubleshooting

- If the health check fails:
  - Verify MongoDB connection
  - Check environment variables
  - Review application logs

- If OAuth authentication fails:
  - Verify redirect URIs in Google Cloud Console
  - Check if BASE_URL matches your actual domain
  - Ensure SSL is properly configured
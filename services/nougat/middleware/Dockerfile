# Dockerfile

# Use an official Node.js runtime as a parent image
# Choose a specific LTS version (e.g., 18) and Alpine for smaller size
FROM node:23-alpine

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install app dependencies using npm ci for faster, more reliable builds
# Use --only=production if you don't need devDependencies in the final image
RUN npm ci --only=production

# Bundle app source
COPY . .

# Make port 3000 available to the world outside this container
# This is the port defined in the .env file (or default in server.js)
EXPOSE 3000

# Check Node.js and npm versions (optional, for build logs)
RUN node -v
RUN npm -v

# Define the command to run your app
CMD [ "node", "index.js" ]
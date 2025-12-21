ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}

# Create the target directory
RUN mkdir -p /opt/scripts

# Copy the install.sh script into the container
COPY install.sh /opt/scripts/install.sh

# Make the script executable and run it
RUN chmod +x /opt/scripts/install.sh && /opt/scripts/install.sh

FROM --platform=$BUILDPLATFORM python:3.11-alpine AS build
RUN pip install --upgrade pip
RUN pip install setuptools>=75.1.0

# Install or update the fixed versions of vulnerable packages
RUN apk add --no-cache \
    busybox \
    ssl_client\
    busybox-binsh
# Update the package index and upgrade existing packages
RUN apk update && \
    apk upgrade --no-cache

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Ensure the SQLite database persists across restarts by creating a volume for it
# VOLUME /mnt

# # Set environment variables (Optional)
# ENV PLAID_CLIENT_ID=your_client_id \
#     PLAID_SECRET=your_secret \
#     PLAID_PUBLIC_TOKEN=your_public_token

RUN adduser -D worker
# RUN chown -R worker:worker /mnt/

USER worker
WORKDIR /app

COPY --chown=worker:worker . .

# Run the app
CMD ["python", "main.py"]

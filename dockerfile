# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.6-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# In case other libraries are needed
RUN \
    apt-get -y update && \
    apt-get install -y --no-install-recommends \
    git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install pip requirements
RUN \
    # python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# CMD ["/bin/sh"]

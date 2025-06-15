# Use a modern, stable Python version
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the file that lists your bot's python libraries
COPY requirements.txt .

# Create a virtual environment (the correct way, without the buggy --copies flag)
RUN python -m venv /opt/venv

# Add the virtual environment to the PATH. This makes it the default python/pip.
ENV PATH="/opt/venv/bin:$PATH"

# Install the libraries from requirements.txt into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt

# Copy all of your bot's code (bot.py) into the container
COPY . .

# Set the command that runs your bot when the container starts
CMD ["python", "bot.py"]

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY mcp.py /app/notebook_client.py

# Set environment variables with the default values
ENV NOTEBOOK_PATH="notebook.ipynb" \
    SERVER_URL="http://localhost:8888" \
    TOKEN="MY_TOKEN"

# Run the script
CMD ["python", "notebook_client.py"]
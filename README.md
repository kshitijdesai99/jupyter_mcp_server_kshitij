# Jupyter MCP Server Client

This repository contains a Docker-based client for connecting to a Jupyter server with multi-collaborative protocol support.

## Prerequisites

- Python 3.12.10
- Docker
- Git

## Setup Instructions

### 1. Set Up Python Environment

```bash
# Create and activate virtual environment
python3.12 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate

# Install package manager
pip install uv

# Install required packages
uv pip install jupyterlab jupyter-collaboration ipykernel pycrdt
uv pip install jupyter-nbmodel-client jupyter_kernel_client

# Fix dependencies (required for compatibility)
pip uninstall -y jupyter_server_ydoc pycrdt
uv pip install jupyter_server_ydoc pycrdt
```

### 2. Create Your Notebook

```bash
# Clone the repository (if needed)
git clone https://github.com/kshitijdesai99/jupyter_mcp_server_kshitij.git
cd jupyter_mcp_server_kshitij

# Create a new notebook
touch notebook.ipynb
```

### 3. Start Jupyter Server

```bash
jupyter lab --port 8888 --IdentityProvider.token MY_TOKEN --ip 0.0.0.0
```

> **Note:** Replace `MY_TOKEN` with your preferred authentication token or just keep it as it is.

## Docker Instructions

### Build the Docker Image

```bash
docker build -t notebook-client .
```

### Run the Client Container --> just for testing not required for mcp

```bash
docker run \
  -e NOTEBOOK_PATH="notebook.ipynb" \
  -e SERVER_URL="http://host.docker.internal:8888" \
  -e TOKEN="MY_TOKEN" \
  notebook-client
```

> **Note:** When running from a different directory, use the full path to your notebook file.

## Claude Desktop Integration

Add this configuration to your Claude desktop `config.json` file:

```json
"jupyter": {
    "command": "docker",
    "args": [
      "run",
      "--rm",
      "-i",
      "-e", "NOTEBOOK_PATH=C:\\Users\\user\\Documents\\Jupyter_MCP\\notebook.ipynb",
      "-e", "SERVER_URL=http://host.docker.internal:8888",
      "-e", "TOKEN=MY_TOKEN",
      "notebook-client"
    ]
}
```

> **Important:** Adjust the `NOTEBOOK_PATH` to match your actual file location.

## Troubleshooting

- Ensure the Jupyter server is running before connecting with the client
- Verify that your token matches between the server and client configuration
- For Windows paths in Docker, use double backslashes as shown in the example

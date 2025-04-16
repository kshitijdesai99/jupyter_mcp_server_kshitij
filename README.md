# Objective - https://github.com/datalayer/jupyter-mcp-server/tree/main to make it more robust
# Used python 3.12.10

# Before you start claude make sure jupyter server is on
python3.12 -m venv env
env\Scripts\activate
pip install uv
uv pip install jupyterlab jupyter-collaboration ipykernel pycrdt
uv pip install jupyter-nbmodel-client jupyter_kernel_client
pip uninstall -y jupyter_server_ydoc pycrdt
uv pip install jupyter_server_ydoc pycrdt

# Create your notebook for example I named it notebook.ipynb
git clone 
touch notebook.ipynb

jupyter lab --port 8888 --IdentityProvider.token MY_TOKEN --ip 0.0.0.0

# commands
docker build -t notebook-client .

# Update your dockerfile with your actual file path or 
# best - run it from the same directory as file

## For Testing ## 
docker run \
  -e NOTEBOOK_PATH="notebook.ipynb" \
  -e SERVER_URL="http://host.docker.internal:8888" \
  -e TOKEN="MY_TOKEN" \
  notebook-client

# add this in you claude desktop config.json
# example for my windows notebook
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


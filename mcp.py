import os
import sys
import asyncio
import logging
from typing import List, Dict, Any

from mcp.server.fastmcp import FastMCP

from jupyter_kernel_client import KernelClient
from jupyter_nbmodel_client import (
    NbModelClient,
    get_jupyter_notebook_websocket_url,
)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("jupyter_mcp")

# Initialize FastMCP server
mcp = FastMCP("jupyter")

# Environment setup
NOTEBOOK_PATH = os.getenv("NOTEBOOK_PATH", "notebook.ipynb")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8888")
TOKEN = os.getenv("TOKEN", "MY_TOKEN")

# Initialize the kernel client
logger.info(f"Initializing kernel client with SERVER_URL={SERVER_URL}")
kernel = KernelClient(server_url=SERVER_URL, token=TOKEN)
kernel.start()
logger.info("Kernel client started successfully")

def extract_output(output: dict) -> str:
    """
    Extracts readable output from a Jupyter cell output dictionary.
    Args:
        output (dict): The output dictionary from a Jupyter cell.
    Returns:
        str: A string representation of the output.
    """
    output_type = output.get("output_type")
    if output_type == "stream":
        return output.get("text", "")
    elif output_type in ["display_data", "execute_result"]:
        data = output.get("data", {})
        if "text/plain" in data:
            return data["text/plain"]
        elif "text/html" in data:
            return "[HTML Output]"
        elif "image/png" in data:
            return "[Image Output (PNG)]"
        else:
            return f"[{output_type} Data: keys={list(data.keys())}]"
    elif output_type == "error":
        return output["traceback"]
    else:
        return f"[Unknown output type: {output_type}]"

@mcp.tool()
async def add_markdown_cell(cell_content: str) -> str:
    """Add a markdown cell in a Jupyter notebook.
    
    Args:
        cell_content: Markdown content to add
    
    Returns:
        str: Success message
    """
    logger.info("Adding markdown cell")
    try:
        notebook = NbModelClient(
            get_jupyter_notebook_websocket_url(server_url=SERVER_URL, token=TOKEN, path=NOTEBOOK_PATH)
        )
        await notebook.start()
        notebook.add_markdown_cell(cell_content)
        await notebook.stop()
        logger.info("Markdown cell added successfully")
        return "Jupyter Markdown cell added."
    except Exception as e:
        logger.error(f"Error adding markdown cell: {str(e)}")
        return f"Error adding markdown cell: {str(e)}"

@mcp.tool()
async def add_execute_code_cell(cell_content: str) -> List[str]:
    """Add and execute a code cell in a Jupyter notebook.
    
    Args:
        cell_content: Python code to execute
    
    Returns:
        list[str]: List of outputs from the executed cell
    """
    logger.info("Adding and executing code cell")
    try:
        notebook = NbModelClient(
            get_jupyter_notebook_websocket_url(server_url=SERVER_URL, token=TOKEN, path=NOTEBOOK_PATH)
        )
        await notebook.start()
        cell_index = notebook.add_code_cell(cell_content)
        logger.info(f"Cell added at index {cell_index}, executing...")
        notebook.execute_cell(cell_index, kernel)
        
        # Wait a moment for execution to complete
        await asyncio.sleep(1)
        
        ydoc = notebook._doc
        outputs = ydoc._ycells[cell_index]["outputs"]
        str_outputs = [extract_output(output) for output in outputs]
        await notebook.stop()
        logger.info(f"Code cell execution complete, got {len(str_outputs)} outputs")
        return str_outputs
    except Exception as e:
        logger.error(f"Error executing code cell: {str(e)}")
        return [f"Error executing code cell: {str(e)}"]

@mcp.tool()
async def read_notebook_content() -> Dict[str, Any]:
    """Read the entire Jupyter notebook content.
    
    Returns:
        dict: The notebook content structure containing cells and metadata
    """
    logger.info("Reading notebook content")
    try:
        notebook = NbModelClient(
            get_jupyter_notebook_websocket_url(server_url=SERVER_URL, token=TOKEN, path=NOTEBOOK_PATH)
        )
        await notebook.start()
        
        # Get the y-document which contains the notebook content
        ydoc = notebook._doc
        
        # Extract all cells
        cells = []
        for i in range(len(ydoc._ycells)):
            cell_type = ydoc._ycells[i]["cell_type"]
            cell_content = ydoc._ycells[i]["source"]
            
            # For code cells, include outputs
            if cell_type == "code":
                outputs = ydoc._ycells[i]["outputs"]
                str_outputs = [extract_output(output) for output in outputs]
                cells.append({
                    "index": i,
                    "type": cell_type,
                    "content": cell_content,
                    "outputs": str_outputs
                })
            else:
                cells.append({
                    "index": i,
                    "type": cell_type,
                    "content": cell_content
                })
        
        await notebook.stop()
        logger.info(f"Read {len(cells)} cells from notebook")
        return {
            "cells": cells,
            "total_cells": len(cells)
        }
    except Exception as e:
        logger.error(f"Error reading notebook content: {str(e)}")
        return {
            "error": str(e),
            "cells": [],
            "total_cells": 0
        }

@mcp.tool()
async def kernel_restart() -> str:
    """Restart the Jupyter kernel.
    
    Returns:
        str: Success message
    """
    logger.info("Restarting kernel")
    try:
        global kernel
        kernel.stop()
        kernel = KernelClient(server_url=SERVER_URL, token=TOKEN)
        kernel.start()
        logger.info("Kernel restarted successfully")
        return "Jupyter kernel restarted successfully"
    except Exception as e:
        logger.error(f"Error restarting kernel: {str(e)}")
        return f"Error restarting kernel: {str(e)}"

async def cleanup_resources():
    """Clean up resources when shutting down."""
    logger.info("Cleaning up resources")
    kernel.stop()
    logger.info("Kernel stopped during shutdown")

if __name__ == "__main__":
    try:
        logger.info("Starting Jupyter MCP server")
        # Try alternate transport methods if stdio fails
        try:
            logger.info("Attempting to run with stdio transport")
            mcp.run(transport='stdio')
        except Exception as e:
            logger.error(f"Error using stdio transport: {str(e)}")
            logger.info("Falling back to TCP transport")
            # Fall back to TCP transport on a standard port (8050)
            mcp.run(transport='tcp', host='localhost', port=8050)
    except Exception as e:
        logger.error(f"Fatal error in MCP server: {str(e)}")
        # Ensure cleanup happens
        asyncio.run(cleanup_resources())
        sys.exit(1)
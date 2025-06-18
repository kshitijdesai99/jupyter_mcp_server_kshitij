import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional

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

# Global notebook client - reuse connection
notebook_client: Optional[NbModelClient] = None

async def get_notebook_client():
    """Get or create a notebook client with connection reuse."""
    global notebook_client
    try:
        if notebook_client is None:
            logger.info("Creating new notebook client")
            notebook_client = NbModelClient(
                get_jupyter_notebook_websocket_url(server_url=SERVER_URL, token=TOKEN, path=NOTEBOOK_PATH)
            )
            await notebook_client.start()
            logger.info("Notebook client connected successfully")
        return notebook_client
    except Exception as e:
        logger.error(f"Error creating notebook client: {str(e)}")
        notebook_client = None
        raise

async def ensure_notebook_connection():
    """Ensure notebook client is connected, reconnect if needed."""
    global notebook_client
    try:
        if notebook_client is None:
            return await get_notebook_client()
        
        # Test connection by trying to access the document
        _ = notebook_client._doc
        return notebook_client
    except Exception as e:
        logger.warning(f"Notebook connection lost, reconnecting: {str(e)}")
        notebook_client = None
        return await get_notebook_client()

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
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Markdown cell addition attempt {attempt + 1}/{max_retries}")
            notebook = await ensure_notebook_connection()
            
            # Add the markdown cell
            cell_index = notebook.add_markdown_cell(cell_content)
            logger.info(f"Markdown cell added at index {cell_index}")
            
            # Wait for the operation to complete
            await asyncio.sleep(0.5)
            
            # Verify the cell was added
            ydoc = notebook._doc
            if cell_index < len(ydoc._ycells):
                cell_type = ydoc._ycells[cell_index]["cell_type"]
                if cell_type == "markdown":
                    logger.info("Markdown cell verified successfully")
                    return "Jupyter Markdown cell added."
                else:
                    logger.warning(f"Cell at index {cell_index} has type {cell_type}, not markdown")
            
            logger.info("Markdown cell added successfully")
            return "Jupyter Markdown cell added."
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed for markdown cell: {str(e)}")
            if attempt < max_retries - 1:
                logger.info("Retrying markdown cell addition...")
                # Reset connection on error
                global notebook_client
                notebook_client = None
                await asyncio.sleep(1)
            else:
                return f"Error adding markdown cell after {max_retries} attempts: {str(e)}"

@mcp.tool()
async def add_execute_code_cell(cell_content: str) -> List[str]:
    """Add and execute a code cell in a Jupyter notebook.
    
    Args:
        cell_content: Python code to execute
    
    Returns:
        list[str]: List of outputs from the executed cell
    """
    logger.info("Adding and executing code cell")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Code cell execution attempt {attempt + 1}/{max_retries}")
            notebook = await ensure_notebook_connection()
            
            # Add the code cell
            cell_index = notebook.add_code_cell(cell_content)
            logger.info(f"Code cell added at index {cell_index}, executing...")
            
            # Execute the cell
            notebook.execute_cell(cell_index, kernel)
            
            # Wait for execution with progressive checking
            max_wait_time = 30  # seconds
            check_interval = 0.5  # seconds
            waited = 0
            
            while waited < max_wait_time:
                await asyncio.sleep(check_interval)
                waited += check_interval
                
                try:
                    ydoc = notebook._doc
                    if cell_index < len(ydoc._ycells):
                        outputs = ydoc._ycells[cell_index]["outputs"]
                        if outputs:  # Has outputs, execution likely complete
                            break
                except Exception as e:
                    logger.warning(f"Error checking outputs during wait: {str(e)}")
                
                if waited % 5 == 0:  # Log every 5 seconds
                    logger.info(f"Still waiting for execution... ({waited}s)")
            
            # Get final outputs
            ydoc = notebook._doc
            outputs = ydoc._ycells[cell_index]["outputs"]
            str_outputs = [extract_output(output) for output in outputs]
            
            logger.info(f"Code cell execution complete, got {len(str_outputs)} outputs")
            return str_outputs
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed for code cell: {str(e)}")
            if attempt < max_retries - 1:
                logger.info("Retrying code cell execution...")
                # Reset connection on error
                global notebook_client
                notebook_client = None
                await asyncio.sleep(1)
            else:
                return [f"Error executing code cell after {max_retries} attempts: {str(e)}"]

@mcp.tool()
async def read_notebook_content() -> Dict[str, Any]:
    """Read the entire Jupyter notebook content.
    
    Returns:
        dict: The notebook content structure containing cells and metadata
    """
    logger.info("Reading notebook content")
    try:
        notebook = await ensure_notebook_connection()
        
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
        global kernel, notebook_client
        
        # Stop current kernel
        kernel.stop()
        
        # Reset notebook client to force reconnection
        if notebook_client:
            try:
                await notebook_client.stop()
            except:
                pass
            notebook_client = None
        
        # Start new kernel
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
    
    global notebook_client
    if notebook_client:
        try:
            await notebook_client.stop()
        except Exception as e:
            logger.warning(f"Error stopping notebook client: {str(e)}")
    
    kernel.stop()
    logger.info("Resources cleaned up")

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
#!/usr/bin/env python3
"""
Mock Agent Server

A simple HTTP server that serves a sample AgentCard file at /.well-known/agent.json
for testing the Agent Registry Service.
"""

import argparse
import logging
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AgentCardHandler(SimpleHTTPRequestHandler):
    """
    HTTP request handler that serves a sample AgentCard.
    """

    def do_GET(self):
        """
        Handle GET requests, serving the AgentCard for /.well-known/agent.json
        """
        if self.path == "/.well-known/agent.json":
            self.serve_agent_card()
        elif self.path == "/":
            self.serve_root()
        else:
            self.send_error(404, "Not Found")

    def serve_agent_card(self):
        """
        Serve the AgentCard JSON file
        """
        try:
            # Use the absolute path to the sample_agent_card.json file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            agent_card_path = os.path.join(script_dir, "sample_agent_card.json")

            with open(agent_card_path, "r") as f:
                agent_card = f.read()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(agent_card.encode())
            logger.info(f"Served AgentCard from {agent_card_path}")
        except Exception as e:
            logger.error(f"Failed to serve AgentCard: {e}")
            self.send_error(500, "Internal Server Error")

    def serve_root(self):
        """
        Serve a simple HTML page at the root
        """
        # Get the local server address for display purposes
        host, port = self.server.server_address
        server_url = f"http://{host}:{port}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Mock Agent Server</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; }}
                .endpoint {{ background: #e8f5e9; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h1>Mock Agent Server</h1>
            <p>This is a mock agent server for testing the Agent Registry Service.</p>
            
            <div class="endpoint">
                <p>The AgentCard is available at: <a href="/.well-known/agent.json">/.well-known/agent.json</a></p>
                <p>Use this URL for registering with the agent registry:</p>
                <pre>{server_url}</pre>
            </div>
            
            <h2>Sample curl command:</h2>
            <pre>curl -X POST http://localhost:8080/register -H "Content-Type: application/json" -d '{{"url": "{server_url}"}}'</pre>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())


def run_server(host="localhost", port=8000):
    """
    Start the HTTP server
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, AgentCardHandler)
    logger.info(f"Starting mock agent server at http://{host}:{port}")
    logger.info(f"AgentCard available at http://{host}:{port}/.well-known/agent.json")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a mock agent server with AgentCard"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind the server (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=8003, help="Port to bind the server (default: 8000)"
    )
    args = parser.parse_args()

    run_server(args.host, args.port)

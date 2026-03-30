import json
import socket
import threading
import os
import mimetypes
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"    # Listen on all interfaces
PORT = 8080          # Default port for HTTP

# Request Parsing Function
def parse_request(data):

    try:
        request_text = data.decode("utf-8")
        lines = request_text.split("\r\n")

        request_line = lines[0]
        method, path, version = request_line.split()

        headers = {}
        body = ""

        i=1

        while lines[i] != "":
            key, value = lines[i].split(": ", 1)
            headers[key] = value
            i += 1
        
        i += 1
        body = "\r\n".join(lines[i:])

        parsed_url = urlparse(path)

        return{
            "method": method,
            "path": parsed_url.path,
            "query": parse_qs(parsed_url.query),
            "version": version,
            "headers": headers,
            "body": body
        }
    
    except Exception as e:
        print(f"Error parsing request: {e}")
        return None
    
# Response Building Function
def build_response(status_code=200, body="", content_type="text/plain"):
    status_messages = {
        200: "OK",
        404: "Not Found",
        500: "Internal Server Error"
    }

    if isinstance(body, str):
        body = body.encode("utf-8")

    response = (
        f"HTTP/1.1 {status_code} {status_messages.get(status_code)}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("utf-8") + body

    print(repr(response))

    return response

# Static File Handler
def serve_static(path):
    file_path = "public" + path

    if not os.path.isfile(file_path):
        return(build_response(404, "File Not Found"))
    
    with open(file_path, "rb") as f:
        content = f.read()

    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return build_response(200, content, mime)

# Routes

def home_handler(req):
    return build_response(200, "Welcome to Chinmay's HTTP Server!")

def hello_handler(req):
    name = req["query"].get("name", ["World"])[0]
    return build_response(200, f"Hello, {name}!")

def json_handler(req):
    data = {
        "message": "This is a JSON response",
        "query": req["query"]
    }
    return build_response(200, json.dumps(data), "application/json")

ROUTES = {
    ("GET", "/"): home_handler,
    ("GET", "/hello"): hello_handler,
    ("GET", "/json"): json_handler
}

#Middleware for logging

def logging_middleware(req, handler):
    print(f"{req['method']} {req['path']}")
    return handler(req)

MIDDLEWARES = [logging_middleware]

def apply_middlewares(req, handler):
    for middleware in reversed(MIDDLEWARES):
        handler = lambda r, h=handler, m=middleware: m(r, h)
    return handler(req)


def handle_client(client_socket):
    try:
        data = client_socket.recv(4096)

        if not data:
            return
        request = parse_request(data)

        if not request:
            response = build_response(500, "Invalid Request")
            client_socket.sendall(response)
            return
        
        method = request["method"]
        path = request["path"]

        if path.startswith("/static/"):
            response = serve_static(path.replace("/static", ""))
        else:
            handler = ROUTES.get((method, path))

            if handler:
                response = apply_middlewares(request, handler)
            else:
                response = build_response(404, "Route Not Found")

        client_socket.sendall(response)

    except Exception as e:
        print(f"Error handling request: {e}")
        response = build_response(500, "Internal Server Error")

    finally:
        client_socket.close()

#Start Server
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Server running on http://{HOST}:{PORT}")

    while True:
        client_socket, addr = server.accept()
        print(f"Connection from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

if __name__ == "__main__":
    start_server()

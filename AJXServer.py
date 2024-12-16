import json
import ure  # type: ignore


class AJXServer:
    def __init__(self, server_socket, port=80):
        self.server_socket = server_socket
        self.port = port
        self.elapsed_time = 0
        self.on_time_value = 0
        self.off_time_value = 0

        # Setter methods (using property decorators is generally preferred in Python)
    @property
    def elapsed_time(self):
        return self._elapsed_time

    @elapsed_time.setter
    def elapsed_time(self, value):
        if isinstance(value, (int, float)):  # Type checking
            self._elapsed_time = value
        else:
            raise TypeError("Elapsed time must be a number")

    @property
    def on_time_value(self):
        return self._on_time_value

    @on_time_value.setter
    def on_time_value(self, value):
        if isinstance(value, (int, float)):  # Type checking
            self._on_time_value = value
        else:
            raise TypeError("On time value must be a number")

    @property
    def off_time_value(self):
        return self._off_time_value

    @off_time_value.setter
    def off_time_value(self, value):
        if isinstance(value, (int, float)):  # Type checking
            self._off_time_value = value
        else:
            raise TypeError("Off time value must be a number")

    def start(self):
        client, addr = self.server_socket.accept()
        print("Client connected from", addr)
        try:
            client.settimeout(0.5)
            request = b""
            try:
                while "\r\n\r\n" not in request:
                    request += client.recv(512)
            except OSError:
                pass

            try:
                request += client.recv(1024)
                print(
                    "Received form data after \\r\\n\\r\\n(i.e. from Safari on macOS or iOS)"
                )
            except OSError:
                pass

            print("Request is:", request.decode())
            if "HTTP" not in request:
                return

            try:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(
                    1
                ).decode("utf-8").rstrip("/")

            except Exception:
                url = ure.search(
                    "(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request
                ).group(1).rstrip("/")
            print("URL is", url)

            try:
                match = ure.search(r"ontime=(\d+)&offtime=(\d+)", request)
                if match:
                    self.on_time_value = (int(match.group(1)))
                    self.off_time_value = int(match.group(2))
                    print(self.on_time_value, self.off_time_value)
            except (ValueError, AttributeError):  # Catch potential errors
                pass

            if url == "":
                self.handle_root(client)
            elif url == "data":
                self.handle_data(client)
            elif url == "submit":
                self.handle_input(client)
            elif url == "submitval":
                self.handle_values(client)
            else:
                self.handle_not_found(client, url)

        finally:
            client.close()

    def handle_root(self, client):
        try:
            with open("index.html", "r") as f:
                html = f.read()
            self.send_response(client, html, "text/html")
        except OSError:
            self.send_response(client, "File not found")

    def handle_input(self, client):
        try:
            with open("input.html", "r") as f:
                html = f.read()
            self.send_response(client, html, "text/html")
        except OSError:
            self.send_response(client, "File not found")

    def handle_values(self, client):
        try:
            with open("index.html", "r") as f:
                html = f.read()
            self.send_response(client, html, "text/html")
        except OSError:
            self.send_response(client, "File not found")

    def handle_data(self, client):
        data = {"ontime": self.on_time_value,
                "offtime": self.off_time_value, "timer": self.elapsed_time}
        json_data = json.dumps(data)
        print(json_data)
        self.send_response(client, json_data, "application/json")

    def handle_not_found(self, client, url):
        self.send_response(client, "Path not found: {}".format(url))

    def send_response(self, client, payload, content_type="text/html"):
        content_length = len(payload)
        client.sendall(f"HTTP/1.0 200 OK\r\n".encode())
        client.sendall(f"Content-Type: {content_type}\r\n".encode())
        client.sendall(f"Content-Length: {content_length}\r\n".encode())
        client.sendall(b"\r\n")
        if content_length > 0:
            client.sendall(payload)
        client.close()

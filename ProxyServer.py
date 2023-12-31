import socket
import threading
import signal
import sys

class ProxyServer:
    def __init__(self, port):
        signal.signal(signal.SIGINT, self.close)
        self.port = port

        self.clients = []

        #Socket init
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSocket.bind(('', self.port))
        self.serverSocket.listen(socket.SOMAXCONN)
        print("Listening on port " + str(port) + "...")

        #Configuration setting
        self.filter_enabled = True
        self.prohibited_words = ["bad","discrimination","violence"]
        self.insert_text = "by Proxy"

    def recvall(self, _socket, timeout = 0.1):
        # recv all data
        data = b""
        _socket.settimeout(timeout) # because browser not end TCP so we need to set timeout for _socket.recv
        try:
            while 1:
                buffer = _socket.recv(1024) # receive buffer
                if (not buffer):
                    break
                data += buffer # add buffer to data
        except: # case timeout
            pass
        return data
    
    def parseURL(self, request):
        return request.decode().split(' ')[1]
    
    def parseHost(self, request):
        if b"Host" in request:
            hostPos = request.find(b"Host") + 6
            data = request[hostPos : request.find(b"\r\n", hostPos)].decode()
        else:
            serverURL = self.parseURL(request)
            if "://" in serverURL:
                data = serverURL.split('/')[2]
            else:
                data = serverURL.split('/')[0]

        if ':' in data:
            return data.split(':')[0], int(data.split(':')[1])
        return data, 80
    
    def start(self):
        # Wait for client to connect and create a thread for each client
        while 1:
            (clientSocket, TSAP) = self.serverSocket.accept()
            print("New connection from: " + str(TSAP))
            self.clients.append(clientSocket)
            thread = threading.Thread(name= TSAP, target = self.client_proxy, args=(clientSocket, TSAP), daemon=True)
            thread.start()

    def filtering(self, content):
        if self.filter_enabled:
            #insert text in the title
            content = content.replace("<title>", f"<title>{self.insert_text}</title>")
            #censor prohibited words
            for word in self.prohibited_words:
                censored_word = '*'*len(word)
                content = content.replace(word,censored_word)
            
            #remove resources in mp4 format
            content = content.replace(".mp4","_blocked.mp4")

        return content 
    
    def remove_header(self,request):
        lines = request.decode().split('\r\n')
        request_lines = []
        for line in lines:
            if not line.startswith("Connection: Keep-Alive","Proxy-Connection: Keep-Alive", "Accept-Encoding: gzip"):
                request_lines.append(line)
        modified_request = '\r\n'.join(request_lines).encode()
        return modified_request

    def client_proxy(self, clientSocket, TSAP):
        # Wait for client to connect and create a thread for each client
        while 1:
            request = self.recvall(clientSocket)
            if len(request) == 0:
                clientSocket.close()
                return
            
            serverAddress, serverPort = self.parseHost(request)
            serverURL = self.parseURL(request)

            #Serving
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.connect((serverAddress, serverPort))
            # if serverPort == 443:
            #     clientSocket.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
            print(request)
            print("------------------")
            #Filtering
            modified_request = self.remove_header(request)
            serverSocket.sendall(modified_request)
            data = self.recvall(serverSocket)
            #censor content
            data = self.filtering(data.decode())
            clientSocket.sendall(data.encode())
            #print(data.decode())
    
    def close(self):
        self._socket.close()
        sys.exit(0)

server = ProxyServer(1234)
server.start()




# request = b"b'GET http://12.47.10.48:12/hehe/haha HTTP/1.1\r\nHost: bullshit.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\nConnection: keep-alive\r\nUpgrade-Insecure-Requests: 1\r\n\r\n'"
# add, po = server.parseHost(request)
# print(add, po)
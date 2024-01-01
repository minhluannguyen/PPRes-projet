import socket
import threading
import signal
import sys
import re
import ssl

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

    def recvall(self, socket, timeout = 1):
        # recv all data
        data = b""
        socket.settimeout(timeout) # because browser not end TCP so we need to set timeout for _socket.recv
        try:
            while 1:
                buffer = socket.recv(1024) # receive buffer
                if (not buffer):
                    break
                data += buffer # add buffer to data
        except: # case timeout
            pass
        return data
    
    def forward_data(self, source, destination):
        print("443------------------2")
        while True:
            data = source.recv(4096)
            if not len(data):
                break
            destination.send(data)
            print(data.decode())
        source.close()
        destination.close()
    
    def filterHeader(self, data):
        data = data.replace(b'HTTP/1.1', b'HTTP/1.0')

        headerRules = [
            "Connection: keep-alive",
            "Proxy-Connection: keep-alive",
            "Accept-Encoding: gzip"
        ]
        headerList = data.decode().split('\r\n')
        # print(headerList)
        filteredList = []
        for field in headerList:
            flag = True
            for rule in headerRules:
                if field.lower().startswith(rule.lower()):
                    flag = False
                    break
            if flag:
                filteredList.append(field)
        
        #filteredList.append("\r\n")
        header = "\r\n".join(filteredList).encode()
        
        return header
    
    def filterData(self, data):
        try:
            dataSegment = data.split(b"\r\n\r\n")
            if len(dataSegment) < 2:
                return data
            header = dataSegment[0]
            body = b''.join(dataSegment[1:])

            # Modify title
            body = re.sub(b'<title>.*?</title>', b'<title>Sufing with Proxy Server</title>', body)

            # Delete all mp4 resources
            body = re.sub(rb'<source.*?type="video/mp4".*?>', b'', body)

            # Censor forhibited words
            prohibitedList = [
                'HTML',
                'site',
                'récompense'
            ]
            for word in prohibitedList:
                body = re.sub(word.encode(), b'*' * len(word), body, flags=re.IGNORECASE)

            # Replace word in giving list
            replaceList = [
                'This:JavaFuckingScript',
                '2023:2024',
            ]
            
            for rule in replaceList:
                key = rule.split(":")[0].encode()
                val = rule.split(":")[1].encode()
                body = re.sub(key, val, body, flags=re.IGNORECASE)
            
            # Recreate response
            data = b"\r\n\r\n".join([header, body])
        except Exception:
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

    def client_proxy(self, clientSocket, TSAP):
        # Wait for client to connect and create a thread for each client
        request = self.recvall(clientSocket)
        if len(request) == 0:
            return clientSocket.close()

        serverAddress, serverPort = self.parseHost(request)
        serverURL = self.parseURL(request)
        print(serverAddress, serverPort, serverURL)

        #Filtering
        #header = request.split(b"\r\n\r\n")[0]
        request = self.filterHeader(request)
        #request = header
        #Censoring

        #Serving
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.connect((serverAddress, serverPort))
        if serverPort == 443:
            # context = ssl.create_default_context()
            # serverSocket = context.wrap_socket(sock=serverSocket, server_hostname=serverAddress)
            # serverSocket.connect((serverAddress, serverPort))

            clientSocket.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            self.forward_data(serverSocket, clientSocket)
        
        print(request)
        print("------------------")
        serverSocket.sendall(request)

        data = self.recvall(serverSocket)
        if not data:
            return
        data = self.filterData(data)
        clientSocket.sendall(data)
        # print(data.decode())

    def close(self):
        self._socket.close()
        sys.exit(0)

server = ProxyServer(1234)
server.start()




# request = b"b'GET http://12.47.10.48:12/hehe/haha HTTP/1.1\r\nHost: bullshit.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\nConnection: keep-alive\r\nUpgrade-Insecure-Requests: 1\r\n\r\n'"
# add, po = server.parseHost(request)
# print(add, po)
import socket
import threading
import signal
import sys
import re

class ProxyServer:
    def __init__(self, port, censorRulesFile, replaceRulesFile):
        signal.signal(signal.SIGINT, self.close)
        self.port = port
        self.censorRulesFile = censorRulesFile
        self.replaceRulesFile = replaceRulesFile

        self.censorRules = self.readListFileRules(self.censorRulesFile)
        self.replaceRules = self.readListFileRules(self.replaceRulesFile)

        #Socket init
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSocket.bind(('', self.port))
        self.serverSocket.listen(socket.SOMAXCONN)
        print("Listening on port " + str(port) + "...")

    def readListFileRules(self, file):
        with open(file, "rb") as f:
            return list(map(lambda x:x.lower(), f.read().strip().splitlines()))

    def recvall(self, socket, timeout = 1):
        # recv all data
        data = b""
        socket.settimeout(timeout) # because browser not end TCP so we need to set timeout for _socket.recv
        try:
            while 1:
                buffer = socket.recv(4096) # receive buffer
                if (not buffer):
                    break
                data += buffer # add buffer to data
        except: # case timeout
            pass
        return data
    
    def forward_data(self, source, destination):
        source.settimeout(1)
        destination.settimeout(1)
        while True:
            data = source.recv(1024)
            if not len(data):
                break
            destination.send(data)
            print(data.decode())
        source.close()
        destination.close()
    
    #Filter header before send to server
    def filterHeader(self, data):
        data = data.replace(b'HTTP/1.1', b'HTTP/1.0')

        headerRules = [
            "Connection: keep-alive",
            "Proxy-Connection: keep-alive",
            "Accept-Encoding: gzip"
        ]
        headerList = data.decode().split('\r\n')
        filteredList = []
        for field in headerList:
            flag = True
            for rule in headerRules:
                if field.lower().startswith(rule.lower()):
                    flag = False
                    break
            if flag:
                filteredList.append(field)
        
        header = "\r\n".join(filteredList).encode()
        return header
    
    #Filter data before send to client
    def filterData(self, data):
        try:
            dataSegment = data.split(b"\r\n\r\n")
            if len(dataSegment) < 2:
                return data
            header = dataSegment[0]
            body = b''.join(dataSegment[1:])

            # Modify title
            body = re.sub(b'<title>.*?</title>', b'<title>Surfing with Proxy Server</title>', body)

            # Delete all mp4 resources
            body = re.sub(rb'<source.*?type="video/mp4".*?>', b'', body)

            # Censor forhibited words, ignore the html tags too ...
            for word in self.censorRules:
                body = re.sub(rb"(?<!<[^>])(%s)(?![^<]*>)" % word, b'*' * len(word), body, flags=re.IGNORECASE)

            # Replace word in giving list            
            for rule in self.replaceRules:
                key = rule.split(b':')[0]
                val = rule.split(b':')[1]
                body = re.sub(rb"(?<!<[^>])(%s)(?![^<]*>)" % key, val, body, flags=re.IGNORECASE)
            
            # Recreate response
            data = b"\r\n\r\n".join([header, body])
        except Exception as e:
            print(e)
            pass
        return data

    #get client's URL from request
    def parseURL(self, request):
        return request.decode().split(' ')[1]
    
    #Get client's hostname from request
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
            thread = threading.Thread(name= TSAP, target = self.client_proxy, args=(clientSocket, TSAP), daemon=True)
            thread.start()

    def client_proxy(self, clientSocket, TSAP):
        # Wait for client to connect and create a thread for each client
        request = self.recvall(clientSocket)
        if len(request) == 0:
            return clientSocket.close()

        # Get client's hostname, port, and URL
        serverAddress, serverPort = self.parseHost(request)
        serverURL = self.parseURL(request)
        print(serverAddress, serverPort, serverURL)

        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.connect((serverAddress, serverPort))

        #Forward HTTPS connections
        if serverPort == 443:
            try:
                # context = ssl.create_default_context()
                # serverSocket = context.wrap_socket(sock=serverSocket, server_hostname=serverAddress)
                # serverSocket.connect((serverAddress, serverPort))

                clientSocket.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                self.forward_data(serverSocket, clientSocket)
            except Exception as e:
                print(e)
            finally:
                clientSocket.close()
                serverSocket.close()
                return
        
        #Change header before send to server
        request = self.filterHeader(request)
        serverSocket.sendall(request)

        # print(request)
        # print("------------------")

        #receive all response from server and send back to client
        while True:
            data = self.recvall(serverSocket)
            print(data)
            if not data:
                break
            data = self.filterData(data) #filter data before send to client
            clientSocket.sendall(data)
        
        serverSocket.close()
        return clientSocket.close()

    def close(self):
        self._socket.close()
        sys.exit(0)

server = ProxyServer(port=8080,
                     censorRulesFile="censorRules.txt",
                     replaceRulesFile="replaceRules.txt"
                    )
server.start()




# request = b"b'GET http://12.47.10.48:12/hehe/haha HTTP/1.1\r\nHost: bullshit.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\nConnection: keep-alive\r\nUpgrade-Insecure-Requests: 1\r\n\r\n'"
# add, po = server.parseHost(request)
# print(add, po)
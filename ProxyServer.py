import socket
import threading
import signal
import sys
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

class ProxyConfig(BaseHTTPRequestHandler):
    def do_GET(self):
        # Get the path from the request
        path = self.path

        # Default response code and content type
        response_code = 200
        content_type = 'text/html'

        # Set the default file to serve (index.html)
        file_to_serve = 'index.html'

        # Map different paths to corresponding HTML files
        flag_filter = False
        if path == '/filter':
            file_to_serve = 'filter.html'
            flag_filter = True
        elif path == '/block':
            file_to_serve = 'blockAccess.html'
        
        try:
            # Open and read the file content
            with open(file_to_serve, 'rb') as file:
                content = file.read()
        except FileNotFoundError:
            response_code = 404
            content = b'File Not Found'

        if flag_filter:
            try:
                paramsEnabled = open("filterRule.txt", 'rb').read()
                paramsReplace = open("replaceRules.txt", 'rb').read()
                paramsCensor = open("censorRules.txt", 'rb').read()
                print(paramsEnabled, paramsReplace, paramsCensor)
                
                if (paramsEnabled == b"true"):
                    content = content.replace(b"{{isEnable}}", b"checked")
                elif (paramsEnabled == b"false"):
                    content = content.replace(b"{{isDisable}}", b"checked")
                content = content.replace(b"{{replaceContent}}", paramsReplace)
                content = content.replace(b"{{censorContent}}", paramsCensor)
            except FileNotFoundError:
                response_code = 404
                content = b'Rule Not Found'
                self.send_response(response_code)
                self.wfile.write(content)
                return

        # Send the response
        self.send_response(response_code)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        # Get the path from the request
        path = self.path
        redirect_path = '/'
        # Map to different corresponding paths 
        if path == '/filter-enabled':
            rule_write = 'filterRule.txt'

            # Handling POST requests
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parsing POST parameters
            params = parse_qs(post_data)

            try:
                # Rewrite config file
                ruleFile = open(rule_write, 'w')
                
                # Check params and update
                if (params["isEnabled"][0] == "true"):
                    ruleFile.write("true")
                elif (params["isEnabled"][0] == "false"):
                    ruleFile.write("false")
                ruleFile.close()
            except FileNotFoundError:
                response_code = 404
                content = b'Rule Not Found'
                self.send_response(response_code)
                self.wfile.write(content)
                return
            
            redirect_path = "/filter"
        elif path == '/replace':
            rule_write = 'replaceRules.txt'

            # Handling POST requests
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parsing POST parameters
            params = parse_qs(post_data)
            params = params["replace"][0]
            print(params)

            try:                
                # Rewrite config file
                ruleFile = open(rule_write, 'w')
                
                # Update
                ruleFile.write(params)                
                ruleFile.close()
            except FileNotFoundError:
                response_code = 404
                content = b'Rule Not Found'
                self.send_response(response_code)
                self.wfile.write(content)
                return
            
            redirect_path = "/filter"
        elif path == '/censor':
            rule_write = 'censorRules.txt'

            # Handling POST requests
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parsing POST parameters
            params = parse_qs(post_data)
            params = params["replace"][0]
            print(params)

            try:        
                # Rewrite config file
                ruleFile = open(rule_write, 'w')
                
                # Update
                ruleFile.write(params)
                
                ruleFile.close()
            except FileNotFoundError:
                response_code = 404
                content = b'Rule Not Found'
                self.send_response(response_code)
                self.wfile.write(content)
                return
            
            redirect_path = "/filter"
        elif path == '/block':
            rule_to_serve = 'blockAccess.html'
            rule_write = 'blockAccessRules.txt'

            # Handling POST requests
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parsing POST parameters
            params = parse_qs(post_data)
            params = params["replace"][0]
            print(params)

            try:
                # Open and read the file content
                with open(rule_to_serve, 'r') as htmlFile:
                    content = htmlFile.read()
                
                ruleFile = open(rule_write, 'w')
                
                # Update
                ruleFile.write(params)
                content = content.replace("{{censorContent}}", params)
                
                ruleFile.close()
            except FileNotFoundError:
                response_code = 404
                content = b'Rule Not Found'
                self.send_response(response_code)
                self.wfile.write(content)
                return
            
            redirect_path = "/block"
        
        # Redirect to refresh page
        self.send_response(301)  # or 302 for temporary redirection
        self.send_header('Location', redirect_path)
        self.end_headers()
class ProxyServer():
    def __init__(self, port, censorRulesFile, replaceRulesFile, blockedRulesFile, isEnabledFile):
        signal.signal(signal.SIGINT, self.close)
        self.port = port
        self.censorRulesFile = censorRulesFile
        self.replaceRulesFile = replaceRulesFile
        self.blockedRulesFile = blockedRulesFile
        self.isEnabledFile = isEnabledFile

        self.isEnabledFilter = self.readFilterRule(self.isEnabledFile)
        self.censorRules = self.readListFileRules(self.censorRulesFile)
        self.replaceRules = self.readListFileRules(self.replaceRulesFile)
        self.blockedRules = self.readListFileRules(self.blockedRulesFile)

        #Socket init
        self.proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.proxySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.proxySocket.bind(('', self.port))
        self.proxySocket.listen(socket.SOMAXCONN)
        print("Listening on port " + str(port) + "...")

    def startServer(self):
        server_address = ('', 8080)
        httpd = HTTPServer(server_address, ProxyConfig)
        print('Config page is running on port 8080...')
        httpd.serve_forever()

    def readListFileRules(self, file):
        try:
            with open(file, "rb") as f:
                return list(map(lambda x:x.lower(), f.read().strip().splitlines()))
        except Exception as e:
            print(e.args)
            sys.exit(1)

    def readFilterRule(self, file):
        try:
            with open(file, "rb") as f:
                isEnable = f.read()
                if (isEnable == b"true"):
                    return True
                elif (isEnable == b"false"):
                    return False
        except Exception as e:
            print(e.args)
            sys.exit(1)

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
    
    def forwardAata(self, source, destination):
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
            
            # Replace word in giving list            
            for rule in self.replaceRules:
                key = rule.split(b':')[0]
                val = rule.split(b':')[1]
                body = re.sub(rb"(?<!<[^>])(%s)(?![^<]*>)" % key, val, body, flags=re.IGNORECASE)

            # Censor forhibited words, ignore the html tags too ...
            for word in self.censorRules:
                body = re.sub(rb"(?<!<[^>])(%s)(?![^<]*>)" % word, b'*' * len(word), body, flags=re.IGNORECASE)

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

        #Start web config
        thread = threading.Thread(name= "Config", target = self.startServer, daemon=True)
        thread.start()

        # Wait for client to connect and create a thread for each client
        while 1:
            (clientSocket, TSAP) = self.proxySocket.accept()
            print("New connection from: " + str(TSAP))
            thread = threading.Thread(name= TSAP, target = self.clientProxy, args=(clientSocket, TSAP), daemon=True)
            thread.start()

    def blockAccess(self, url):
        for blocked_url in self.blockedRules:
            if re.search(blocked_url.decode(), url):
                return True  # Access blocked            
        return False  # Access allowed
    
    def updateConfig(self):
        self.isEnabledFilter = self.readFilterRule(self.isEnabledFile)
        self.censorRules = self.readListFileRules(self.censorRulesFile)
        self.replaceRules = self.readListFileRules(self.replaceRulesFile)
        self.blockedRules = self.readListFileRules(self.blockedRulesFile)

    def clientProxy(self, clientSocket, TSAP):
        # Wait for client to connect and create a thread for each client
        request = self.recvall(clientSocket)
        if len(request) == 0:
            clientSocket.close()
            return
        
        # Get client's hostname, port, and URL
        serverAddress, serverPort = self.parseHost(request)
        serverURL = self.parseURL(request)
        print(serverAddress, serverPort, serverURL)

        #update config
        self.updateConfig()
        # Check if access is blocked
        try:
            if self.blockAccess(serverURL):
                # Access is blocked, you can close the connection or send a notification
                clientSocket.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\nAccess to this URL is blocked.")
                clientSocket.close()
                return
        except Exception as e:
            print(e.args)
            clientSocket.close()
            return

        # Create socket to connect to server
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.connect((serverAddress, serverPort))

        #Forward HTTPS connections
        if serverPort == 443:
            try:
                clientSocket.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                self.forwardAata(serverSocket, clientSocket)
            except Exception as e:
                print(e.args)
                clientSocket.close()
                serverSocket.close()
                return
        
        # Change header before send to server
        request = self.filterHeader(request)
        serverSocket.sendall(request)

        # Receive all response from server and send back to client
        while True:
            data = self.recvall(serverSocket)
            print(data)
            if not data:
                break
            if self.isEnabledFilter:
                data = self.filterData(data) #filter data before send to client (if enabled)
            clientSocket.sendall(data)
        
        serverSocket.close()
        return clientSocket.close()

    def close(self):
        self.socket.close()
        sys.exit(0)

server = ProxyServer(port=1234,
                     censorRulesFile="censorRules.txt",
                     replaceRulesFile="replaceRules.txt",
                     blockedRulesFile="blockAccessRules.txt",
                     isEnabledFile="filterRule.txt"
                    )
server.start()
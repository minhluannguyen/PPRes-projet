import socket
import signal
import sys

class ProxyServer:
    def __init__(self, port):
        signal.signal(signal.SIGINT, self.close)
        self.port = port


        #Socket init
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSocket.bind(('', self.port))
        self.serverSocket.listen(socket.SOMAXCONN)
        print("Écoute sur le port " + str(port) + "...")
    
    def start(self):
        while 1:
            (newConnection, TSAP) = self.serverSocket.accept()
            print("Connection from: " + str(TSAP))
            while 1:
                ligne = newConnection.recv(1234)
                if not ligne:
                    break
                print(ligne)
    
    def close(self):
        self._socket.close()
        sys.exit(0)

server = ProxyServer(1234)
server.start()
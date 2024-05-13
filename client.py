import socket

class Client:
    def __init__(self, server_ip, server_port):
        self.username = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((server_ip, server_port))
    
    def send(self, message, data=b""):
        if message.startswith("file_content"):
            content = message.split("@")
            sender = content[1].encode("utf-8")
            receiver = content[2].encode("utf-8")
            total = message[:12].encode("utf-8") + bytes([len(sender), len(receiver)]) + sender + receiver + data
        elif message.startswith("voice_content"):
            content = message.split("@")
            sender = content[1].encode("utf-8")
            receiver = content[2].encode("utf-8")
            total = message[:13].encode("utf-8") + bytes([len(sender), len(receiver)]) + sender + receiver + data
        else:
            total = message.encode('utf-8')
        length = len(total)
        lenbt = bytes([length // 256, length % 256])
        self.socket.sendall(lenbt + total)

    def recv(self):
        message = b""

        lenbt = self.socket.recv(2)
        length = lenbt[0] * 256 + lenbt[1]

        while length > len(message):
            message += self.socket.recv(length - len(message))
                
        if message[:12].decode('utf-8') == "file_content":
            sender_len = message[12]
            sender = message[13:13 + sender_len].decode('utf-8')
            return f"{message[:12].decode('utf-8')}@{sender}", message[13 + sender_len:]
        
        elif message[:13].decode('utf-8') == "voice_content":
            sender_len = message[13]
            sender = message[14:14 + sender_len].decode('utf-8') 
            return f"{message[:13].decode('utf-8')}@{sender}", message[14 + sender_len:]
        else:
            return message.decode('utf-8'), b""
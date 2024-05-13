import socket
import threading
import os
import datetime


class Server:
    def __init__(self, server_ip, server_port):
        self.online_users = {}
        self.user_credentials = "users_credentials.txt"

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((server_ip, server_port))
        self.socket.listen(5)
        print("服务器监听中")

        self.choice = 0
    
    def send(self, client_socket, message, data=b""):
        if message.startswith("file_content"):
            content = message.split("@")
            sender = content[1].encode("utf-8")
            total = message[:12].encode("utf-8") + bytes([len(sender)]) + sender + data
        elif message.startswith("voice_content"):
            content = message.split("@")
            sender = content[1].encode("utf-8")
            total = message[:13].encode("utf-8") + bytes([len(sender)]) + sender + data
        else:
            total = message.encode('utf-8')

        length = len(total)
        lenbt = bytes([length // 256, length % 256])
        try:
            client_socket.sendall(lenbt + total)
        except socket.error:
            self.quitt(client_socket)

    def recv(self, client_socket):
        try:
            message = b""
            lenbt = client_socket.recv(2)
            
            length = lenbt[0] * 256 + lenbt[1]
            while length > len(message):
                message += client_socket.recv(length - len(message))       
        except socket.error:
            self.quitt(client_socket)
        else:
            if message[:12].decode('utf-8') == "file_content":
                sender_len = message[12]
                receiver_len = message[13]
                sender = message[14:14 + sender_len].decode('utf-8')
                receiver = message[14 + sender_len: 14 + sender_len + receiver_len].decode('utf-8')
                return f"{message[:12].decode('utf-8')}@{sender}@{receiver}", message[14 + sender_len + receiver_len:]
            
            elif message[:13].decode('utf-8') == "voice_content":
                sender_len = message[13]
                receiver_len = message[14]
                sender = message[15:15 + sender_len].decode('utf-8') 
                receiver = message[15 + sender_len: 15 + sender_len + receiver_len].decode('utf-8')
                return f"{message[:13].decode('utf-8')}@{sender}@{receiver}", message[15 + sender_len + receiver_len:]
           
            else:
                return message.decode('utf-8'), b""


    def update(self, user, operation):
        for username, socket in self.online_users.items():
            self.send(socket, f"update@{operation}@{user}")
        if operation == "add_user":
            for username, socket in self.online_users.items():
                if user != username:
                    self.send(self.online_users[user], f"update@{operation}@{username}")


    def quitt(self, client_socket):
        for username, sock in self.online_users.items():
            if client_socket == sock:
                del self.online_users[username]
                print(f"disconnected by {username}")
                self.update(username, "del_user")
                break

        raise SystemExit

############################################################验证登录
    def login(self, client_socket, message):
        content = message.split("@")
        username = content[0]
        password = content[1]
        with open(self.user_credentials, "r") as f:
            f.seek(0)
            lines = f.readlines()
            flag = False
            for line in lines:
                content = line.strip().split()
                if content[0] == username:
                    flag = True
                    if content[1] == password:
                        self.online_users[username] = client_socket
                        print(f"connected by {username}")
                        self.send(client_socket, f"login success")
                        self.update(username, "add_user")
                        threading.Thread(target=self.handle_offline_file).start()
                    else:
                        self.send(client_socket, f"login wrong")
                    break
            if not flag:
                self.send(client_socket, f"login wrong")

    def register(self, client_socket, message):
        content = message.split("@")
        username = content[0]
        password = content[1]
        with open(self.user_credentials, "a+") as f:
            f.seek(0)
            lines = f.readlines()
            flag = False
            for line in lines:
                content = line.strip().split()
                if content[0] == username:
                    flag = True
                    self.send(client_socket, f"register wrong")
                    break
            if not flag:
                f.write(f"{username} {password}\n")
                self.online_users[username] = client_socket
                print(f"user：{username} 注册成功")
                self.send(client_socket, f"register wrong")
                self.update(username, "add_user")

#################################################################文字聊天
    def group_message(self, client_socket, message):
        content = message.split("@")
        sender = content[0]
        send_time = content[1]
        message = content[2]
        for username, sock in self.online_users.items():
            if sock != client_socket:
                self.send(sock, f"group@{sender}@{send_time}@{message}")

    def private_message(self, client_socket, message):
        content = message.split("@")
        sender = content[0]
        receiver = content[1]
        send_time = content[2]
        message = content[3]
        if receiver in self.online_users:
            receiver_socket = self.online_users[receiver]
            if receiver_socket != client_socket:
                self.send(receiver_socket, f"private@{sender}@{receiver}@{send_time}@{message}")


#################################################################传输文件
    def handle_file(self, client_socket, message, data):
        if message.startswith("request"):
            content = message.split("@")
            sender = content[1]
            receiver = content[2]
            file_name = content[3]
            file_size = content[4]
            with open(self.user_credentials, "r") as f:
                f.seek(0)
                lines = f.readlines()
                flag = False
                for line in lines:
                    content = line.strip().split()
                    if content[0] == receiver:
                        flag = True
                        if receiver in self.online_users:
                            self.send(self.online_users[receiver], f"file_request@{sender}@{file_name}@{file_size}")
                        else:
                            self.send(client_socket, f"file_offline_send")
                        break
                if not flag:
                    self.send(client_socket, "file_wronguser")       
        elif message.startswith("content"):
            content = message.split("@")
            file_name = content[1]
            receiver = content[2]
            if receiver == "server":
                with open(file_name, "ab") as f:
                    f.write(data)
            else:
                self.send(self.online_users[receiver], f"file_content@{file_name}", data)
        elif message.startswith("accept"):
            content = message.split("@")
            receiver = content[2]
            if receiver == "server":
                self.choice = 1
            else:
                self.send(self.online_users[receiver], f"file_accept")
        elif message.startswith("reject"):
            content = message.split("@")
            receiver = content[2]
            if receiver == "server":
                self.choice = 2
            else:
                self.send(self.online_users[receiver], f"file_reject")       
        elif message.startswith("over"):
            content = message.split("@")
            sender = content[1]
            receiver = content[2]
            file_name = content[3]
            file_size = content[4]
            target = content[5]
            if receiver == "server":
                with open("tempfile.txt", "ab") as f:
                    f.write(f"{sender}@{target}@{file_name}@{file_size}@PREPARED\n".encode("utf-8"))
                threading.Thread(target=self.handle_offline_file).start()
            else:
                self.send(self.online_users[receiver], f"file_over@{file_name}")



    def handle_offline_file(self):
        if os.path.isfile("tempfile.txt"):
            with open("tempfile.txt", "rb+") as f:
                f.seek(0)
                line = f.readline().decode("utf-8").rstrip()
                while line:
                    if line.endswith("COMPLETE"):
                        line = f.readline().decode("utf-8").rstrip()
                        continue
                    content = line.split("@")
                    sender = content[0]
                    receiver = content[1]
                    file_name = content[2]
                    file_size = content[3]
                    if receiver not in self.online_users:

                        line = f.readline().decode("utf-8").rstrip()
                        continue

                    self.send(self.online_users[receiver], f"file_offrequest@{sender}@{file_name}@{file_size}")

                    while not self.choice:
                        continue

                    if self.choice == 1:
                        message = f"file_content@{file_name}"
                        with open(file_name, "rb") as f1:
                            f1.seek(0)
                            total = 0
                            while total < int(file_size):
                                data = f1.read(1024)
                                total += len(data)
                                self.send(self.online_users[receiver], message, data)
                        
                        total = 0
                        self.send(self.online_users[receiver], f"file_over@{file_name}")

                    os.remove(file_name)
                    f.seek(-9, 1)
                    f.write("COMPLETE\n".encode("utf-8"))
                    self.choice = 0
                    line = f.readline().decode("utf-8").rstrip()


########################################################################语音通话
    def handle_voice(self, message, data):

        if message.startswith("request"):
            content = message.split("@")
            sender = content[1]
            receiver = content[2]
            self.send(self.online_users[receiver], f"voice_request@{sender}")

        elif message.startswith("accept"):
            content = message.split("@")
            receiver = content[2]
            self.send(self.online_users[receiver], f"voice_accept")

        elif message.startswith("reject"):
            content = message.split("@")
            receiver = content[2]
            self.send(self.online_users[receiver], f"voice_reject")

        elif message.startswith("content"):
            content = message.split("@")
            sender = content[1]
            receiver = content[2]
            self.send(self.online_users[receiver], f"voice_content@{sender}", data)

        elif message.startswith("over"):
            content = message.split("@")
            sender = content[1]
            receiver = content[2]
            self.send(self.online_users[receiver], f"voice_over@{sender}")


##########################################################################################
    def handle_client(self, client_socket):
        while True:
            message, data = self.recv(client_socket)
            if message.startswith("login"):
                self.login(client_socket, message[6:])
            elif message.startswith("register"):
                self.register(client_socket, message[9:])
            elif message.startswith("group"):
                self.group_message(client_socket, message[6:])
            elif message.startswith("private"):
                self.private_message(client_socket, message[8:])
            elif message.startswith("file"):
                self.handle_file(client_socket, message[5:], data)
            elif message.startswith("voice"):
                self.handle_voice(message[6:], data)

    def run(self):
        while True:
            client_socket, _ = self.socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    server_ip = "0.0.0.0"
    #server_ip = "127.0.0.1"
    server_port = 9999

    server = Server(server_ip, server_port)
    server.run()

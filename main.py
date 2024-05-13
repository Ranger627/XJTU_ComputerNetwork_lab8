from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import filedialog
from tkinter import simpledialog
import tkinter as tk
import socket
import threading
import os
import time
import datetime
import pyaudio
from client import *


#############################################################################登陆界面
class UI_login:
    def __init__(self, client):
        self.client = client
        self.window = tk.Tk()
        self.window.geometry("300x300")
        self.window.title("登陆界面")
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.label_user = tk.Label(self.window, text="用户名：")
        self.label_user.place(x=30, y=60)
        self.entry_user = tk.Entry(self.window)
        self.entry_user.place(x=90, y=60)
        self.label_pwd = tk.Label(self.window, text="密码：")
        self.label_pwd.place(x=30, y=120)
        self.entry_pwd = tk.Entry(self.window, show='*')
        self.entry_pwd.place(x=90, y=120)

        self.login_button = tk.Button(self.window, text="登录", command=self.login)
        self.login_button.place(x=135, y=165)
        self.register_button = tk.Button(self.window, text="注册", command=self.register)
        self.register_button.place(x=135, y=210)

        self.window.mainloop()

    def login(self):
        self.client.username = self.entry_user.get()
        self.client.send(f"login@{self.client.username}@{self.entry_pwd.get()}")
        message, _ = self.client.recv()
        if message.startswith("login success"):
            self.window.destroy()
        elif message.startswith("login wrong"):
            messagebox.showerror('错误', "用户名或密码错误")

    def register(self):
        self.client.username = self.entry_user.get()
        self.client.send(f"register@{self.client.username}@{self.entry_pwd.get()}")
        message, _ = self.client.recv()
        if message.startswith("register success"):
            self.window.destroy()
        elif message.startswith("register wrong"):
            messagebox.showerror('错误', "该用户已存在，请重新输入用户名")

    def close(self):
        self.client.socket.close()
        self.window.destroy()
        raise SystemExit

#############################################################################聊天界面
class UI_chat:
    def __init__(self, client):
        self.client = client
        self.choice = 0
        self.is_accepted = 0
        self.window = tk.Tk()
        self.window.geometry("600x600")
        self.window.title(f"{self.client.username}的聊天室")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        # 消息界面
        self.text = scrolledtext.ScrolledText(self.window, width=45, height=24)
        self.text.place(x=5, y=5)
        # 在线用户列表
        self.online_userlist = tk.Listbox(self.window, selectmode="single", width=15, height=12)
        self.online_userlist.place(x=390, y=45)
        # 消息输入
        self.input = tk.Text(self.window,width=30, height=15)
        self.input.place(x=75, y=360)
        self.label1 = tk.Label(self.window,text="在线用户")
        self.label1.place(x=390, y=15)
        self.label2 = tk.Label(self.window, text="输入：")
        self.label2.place(x=6, y=360)
        self.group_button = tk.Button(self.window, text="发送群聊", command=self.send_group_message)
        self.group_button.place(x=420, y=300)
        self.private_button = tk.Button(self.window, text="发送私聊", command=self.send_private_message)
        self.private_button.place(x=420, y=360)
        # 传输文件
        self.send_button = tk.Button(self.window, text="传输文件", command=self.send_file)
        self.send_button.place(x=420, y=420)
        # 语音通话
        self.voice_button = tk.Button(self.window, text="语音通话", command=self.send_voice)
        self.voice_button.place(x=420, y=480)
        # 语音通话参数
        chunk_size = 1024
        audio_format = pyaudio.paInt16
        channels = 1 
        rate = 20000 
        self.playing_stream = pyaudio.PyAudio().open(format=audio_format, channels=channels, rate=rate, output=True,
                                                     frames_per_buffer=chunk_size)
        self.recording_stream = pyaudio.PyAudio().open(format=audio_format, channels=channels, rate=rate, input=True,
                                                       frames_per_buffer=chunk_size)

        self.recv_t = threading.Thread(target=self.recv)
        self.recv_t.setDaemon(True)
        self.recv_t.start()
        self.window.mainloop()

    def close(self):
        self.client.socket.close()
        self.window.destroy()
        raise SystemExit

    def update(self, message):
        user = message[9:]
        if message.startswith("add_user"):
            self.online_userlist.insert(tk.END, user)
        elif message.startswith("del_user"):
            for i in range(self.online_userlist.size()):
                if self.online_userlist.get(i) == user:
                    self.online_userlist.delete(i)
                    break

###################################################################################文字聊天
    def send_group_message(self):
        message = self.input.get("1.0", tk.END)
        send_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        self.client.send(f"group@{self.client.username}@{send_time}@{message}")

        self.text.insert(tk.END, f"{self.client.username} ——> 所有人 ({send_time}):\n{message}\n")
        self.text.see(tk.END)

    def send_private_message(self):
        receiver = self.online_userlist.get("anchor")

        if receiver:
            message = self.input.get("1.0", tk.END)
            send_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            self.client.send(f"private@{self.client.username}@{receiver}@{send_time}@{message}")

            self.text.insert(tk.END, f"{self.client.username} ——> {receiver} ({send_time}):\n{message}\n")
            self.text.see(tk.END)
        else:
            messagebox.showerror("错误", "请选择私聊对象")

    def recv_group_message(self, message):
        content = message.split("@")
        sender = content[0]
        send_time = content[1]
        message = content[2]
        self.text.insert(tk.END, f"{sender} ——> 所有人 ({send_time}):\n{message}\n")
        self.text.see(tk.END)

    def recv_private_message(self, message):
        content = message.split("@")
        #print(content)
        sender = content[0]
        receiver = content[1]
        send_time = content[2]
        message = content[3]

        if receiver == self.client.username:
            self.text.insert(tk.END, f"{receiver} <—— {sender} ({send_time}):\n{message}\n")
            self.text.see(tk.END)

######################################################################################### 传输文件
    def send_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            receiver = simpledialog.askstring("传输文件", "请输入文件传输对象")
            if receiver:
                self.client.send(f"file_request@{self.client.username}@{receiver}@{file_name}@{file_size}")
                threading.Thread(target=self.file_thread, args=(receiver, file_path, file_size, )).start()
 
    def recv_file(self, message, data):
        if message.startswith("request"):
            content = message.split("@")
            sender = content[1]
            if messagebox.askyesno("传输文件", f"{sender}给你发送了一个文件，是否接收？"):
                self.client.send(f"file_accept@{self.client.username}@{sender}")
            else:
                self.client.send(f"file_reject@{self.client.username}@{sender}")
        elif message.startswith("accept"):
            self.choice = 1
        elif message.startswith("reject"):
            messagebox.showerror("错误", "对方拒绝接收文件")
        elif message.startswith("content"):
            content = message.split("@")
            file_name = content[1]
            with open(file_name, "ab") as f:
                f.write(data)
        elif message.startswith("over"):
            messagebox.showinfo("文件传输", "文件接收完成")
        elif message.startswith("offline_send"):
            self.choice = 2        
        elif message.startswith("offrequest"):
            content = message.split("@")
            sender = content[1]
            file_name = content[2]
            if messagebox.askyesno("文件传输", f"{sender}给你发送了一个离线文件，是否接收？"):
                self.client.send(f"file_accept@{self.client.username}@server")
            else:
                self.client.send(f"file_reject@{self.client.username}@server")
        elif message.startswith("wronguser"):
            messagebox.showerror("错误", "不存在该用户")

    def file_thread(self, receiver, file_path, file_size):
        while not self.choice:
            continue
        if self.choice == 1:
            file_name = os.path.basename(file_path)
            target = receiver

            file_window = tk.Toplevel(self.window)
            file_window.title("传输文件")
            file_window.protocol("WM_DELETE_WINDOW")
            tk.Label(file_window, text=f"{file_name}文件上传中").pack()
            message = f"file_content@{file_name}@{receiver}"
            with open(file_path, "rb") as f:
                f.seek(0)
                total = 0
                while self.choice != 0 and total < file_size:
                    data = f.read(1024)
                    total += len(data)
                    self.client.send(message, data)
            file_window.destroy()
            total = 0
            self.client.send(f"file_over@{self.client.username}@{receiver}@{file_name}@{file_size}@{target}")
            messagebox.showinfo("文件传输", f"文件发送完成")
            self.choice = 0
        if self.choice == 2:
            file_name = os.path.basename(file_path)
            target = receiver
            receiver = "server"

            file_window = tk.Toplevel(self.window)
            file_window.title("文件传输")
            file_window.protocol("WM_DELETE_WINDOW")
            tk.Label(file_window, text=f"{file_name}文件上传中").pack()
            message = f"file_content@{file_name}@{receiver}"
            with open(file_path, "rb") as f:
                f.seek(0)
                total = 0
                while self.choice != 0 and total < file_size:
                    data = f.read(1024)
                    total += len(data)
                    self.client.send(message, data)
            file_window.destroy()
            total = 0
            self.client.send(f"file_over@{self.client.username}@{receiver}@{file_name}@{file_size}@{target}")
            messagebox.showinfo("文件传输", f"文件发送完成")
            self.choice = 0

    

########################################################################################## 语音通话
    def send_voice(self):
        receiver = self.online_userlist.get("anchor")
        
        if receiver:
            self.client.send(f"voice_request@{self.client.username}@{receiver}")
            threading.Thread(target=self.voice_thread, args=(receiver, )).start()
        else:
            messagebox.showerror("错误", "请选择你的通话对象")

    def recv_voice(self, message, data):
        if message.startswith("request"):
            content = message.split("@")
            sender = content[1]
            flag = messagebox.askyesno("语音通话", f"{sender}想和你进行语音通话，是否接受？")
            if flag:
                self.client.send(f"voice_accept@{self.client.username}@{sender}")
                threading.Thread(target=self.voice_thread, args=(sender,)).start()
                self.is_accepted = 1
            else:
                self.client.send(f"voice_reject@{self.client.username}@{sender}")
        
        elif message.startswith("accept"):
            self.is_accepted = 1

        elif message.startswith("reject"):
            self.is_accepted = 2

        elif message.startswith("content"):
            self.playing_stream.write(data)

        elif message.startswith("over"):
            messagebox.showinfo("语音通话", "语音通话已结束")

    def voice_thread(self, receiver):
        while not self.is_accepted:
            continue

        if self.is_accepted == 1:
            voice_window = tk.Toplevel(self.window)
            voice_window.title("语音通话")
            tk.Label(voice_window, text=f"通话中...").pack()
            voice_window.protocol("WM_DELETE_WINDOW", self.voice_done)

            message = f"voice_content@{self.client.username}@{receiver}"
            while self.is_accepted == 1:
                data = self.recording_stream.read(1024)
                self.client.send(message, data)

            voice_window.destroy()
            self.client.send(f"voice_over@{self.client.username}@{receiver}")
        
        elif self.is_accepted == 2:
            messagebox.showerror("错误", "对方已拒绝")
            self.is_accepted = 0

    def voice_done(self):
        self.is_accepted = 0
################################################################################################
    def recv(self):
        while True:
            message, data = self.client.recv()
            if message.startswith("update"):
                self.update(message[7:])
            elif message.startswith("group"):
                self.recv_group_message(message[6:])
            elif message.startswith("private"):
                self.recv_private_message(message[8:])
            elif message.startswith("file"):
                self.recv_file(message[5:], data)
            elif message.startswith("voice"):
                self.recv_voice(message[6:], data)

############################################################################################
if __name__ == '__main__':
    server_ip = "101.37.161.103" 
    #server_ip = "127.0.0.1" 
    server_port = 9999

    client = Client(server_ip, server_port)
    UI_login(client)
    UI_chat(client)
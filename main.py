import os
import socket
import threading
import time
import gbn

HOST_Send = '127.0.0.1'
HOST_Receive = ''
PORT_Client = 10245
PORT_Server = 9689
ADDR_Target_C = (HOST_Send, PORT_Server)
ADDR_Target_S = (HOST_Send, PORT_Client)
ADDR_Receive_C = (HOST_Receive, PORT_Client)
ADDR_Receive_S = (HOST_Receive, PORT_Server)

CLIENT_DIR = os.path.dirname(__file__) + '/client'
SERVER_DIR = os.path.dirname(__file__) + '/server'

senderSocket_Client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
senderSocket_Server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sender_client = gbn.GBNSender(senderSocket_Client,ADDR_Target_C,'Client')
sender_server = gbn.GBNSender(senderSocket_Server,ADDR_Target_S,'Server') # 两个套接字用作各自的发送


receiverSocket_Client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiverSocket_Server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiverSocket_Client.bind(ADDR_Receive_C)
receiverSocket_Server.bind(ADDR_Receive_S)               # 两个接收套接字用于各自的接收
receiver_client = gbn.GBNReceiver(receiverSocket_Client,'Client')
receiver_server = gbn.GBNReceiver(receiverSocket_Server,'Server')

fpS_Client = open(CLIENT_DIR + '/蝴蝶.jpg', 'rb')
fpS_Server = open(SERVER_DIR + '/南操.jpg', 'rb')
fpR_Client = open(CLIENT_DIR + '/' + str(int(time.time())) + '.jpg', 'ab')
fpR_Server = open(SERVER_DIR + '/' + str(int(time.time())) + '.jpg', 'ab')



# 开启两个线程
Thread_Client_Send = threading.Thread(target=gbn.SendProcess, args=(sender_client, fpS_Client,'Client',))
Thread_Server_Send = threading.Thread(target=gbn.SendProcess, args=(sender_server, fpS_Server,'Server',))
Thread_Client_Receive = threading.Thread(target=gbn.ReceiveProcess, args=(receiver_client, fpR_Client,'Client',))
Thread_Server_Receive = threading.Thread(target=gbn.ReceiveProcess, args=(receiver_server, fpR_Server,'Server',))

Thread_Client_Send_SR = threading.Thread(target=gbn.SendProcess_SR, args=(sender_client, fpS_Client,'Client',))
Thread_Server_Send_SR = threading.Thread(target=gbn.SendProcess_SR, args=(sender_server, fpS_Server,'Server',))
Thread_Client_Receive_SR = threading.Thread(target=gbn.ReceiveProcess_SR, args=(receiver_client, fpR_Client,'Client',))
Thread_Server_Receive_SR = threading.Thread(target=gbn.ReceiveProcess_SR, args=(receiver_server, fpR_Server,'Server',))

# Thread_Client_Send.start()           # GBN,若运行GBN就把这四行注释取消并把下面SR的4行注释掉
# Thread_Server_Send.start()
# Thread_Client_Receive.start()
# Thread_Server_Receive.start()

Thread_Client_Send_SR.start()          # SR,若运行SR就把这四行注释取消并把上面GBN的4行注释掉
Thread_Server_Send_SR.start()
Thread_Client_Receive_SR.start()
Thread_Server_Receive_SR.start()
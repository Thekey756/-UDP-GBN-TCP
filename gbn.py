"""
gbn.py
~~~~~~
This module implements the sender and receiver of Go-Back-N Protocol.

:copyright: (c) 2018 by ZiHuan Wang.
:date: 2019/10/29
:changed by: Zhengkang Guo
:date: 2022/6/10
"""
import random
import socket
import struct
import time


BUFFER_SIZE = 4096
TIMEOUT = 4
WINDOW_SIZE = 3
LOSS_RATE = 0.1


def getChecksum(data):
    """
    char_checksum 按字节计算校验和。每个字节被翻译为无符号整数
    @param data: 字节串
    """
    length = len(str(data))
    checksum = 0
    for i in range(0, length):
        checksum += int.from_bytes(bytes(str(data)[i], encoding='utf-8'), byteorder='little', signed=False)
        checksum &= 0xFF  # 强制截断

    return checksum


class GBNSender:
    def __init__(self, senderSocket, address,who, timeout=TIMEOUT,
                    windowSize=WINDOW_SIZE, lossRate=LOSS_RATE):
        self.sender_socket = senderSocket
        self.timeout = timeout
        self.address = address
        self.window_size = windowSize
        self.loss_rate = lossRate
        self.send_base = 0
        self.next_seq = 0
        self.packets = [None] * 256
        self.who = who

    def udp_send(self, pkt):
        if self.loss_rate == 0 or random.randint(0, int(1 / self.loss_rate)) != 1:
            self.sender_socket.sendto(pkt, self.address)
        else:
            print(self.who,' Packet lost.')
        time.sleep(0.2)

    def wait_ack(self):
        self.sender_socket.settimeout(self.timeout)

        count = 0
        while True:
            if count >= 10:
                # 连续超时10次，接收方已断开，终止
                break
            try:
                data, address = self.sender_socket.recvfrom(BUFFER_SIZE)

                ack_seq, expect_seq = self.analyse_pkt(data)
                print(self.who,' Sender receive ACK:ack_seq', ack_seq, "expect_seq",expect_seq)
                print(self.who," SEND WINDOW: ",ack_seq)
                if (self.send_base == (ack_seq + 1) % 256):
                    # 收到重复确认, 此处应当立即重发
                    pass
                    # for i in range(self.send_base, self.next_seq):
                    #     print('Sender resend packet:', i)
                    #     self.udp_send(self.packets[i])

                self.send_base = max(self.send_base, (ack_seq + 1) % 256) ##窗口滑动
                if self.send_base == self.next_seq:  # 已发送分组确认完毕

                    self.sender_socket.settimeout(None)
                    return True

            except socket.timeout:
                # 超时，重发分组.              ##回退N步
                print(self.who,' Sender wait for ACK timeout.')
                for i in range(self.send_base, self.next_seq):
                    print('Sender resend packet:', i)
                    self.udp_send(self.packets[i])
                self.sender_socket.settimeout(self.timeout)  # reset timer
                count += 1
        return False

    def make_pkt(self, seqNum, data, checksum, stop=False):
        """
        将数据打包
        """
        flag = 1 if stop else 0
        return struct.pack('BBB', seqNum, flag, checksum) + data

    def analyse_pkt(self, pkt):
        """
        分析数据包
        """
        ack_seq = pkt[0]
        expect_seq = pkt[1]
        return ack_seq, expect_seq

    def wait_ack_SR(self, senderSentSet, senderReceivedACKSet):
        self.sender_socket.settimeout(self.timeout)

        count = 0
        while True:
            if count >= 10:
                # 连续超时10次，接收方已断开，终止
                break
            try:
                data, address = self.sender_socket.recvfrom(BUFFER_SIZE)

                ack_seq, expect_seq = self.analyse_pkt(data)
                print(self.who,' Sender receive ACK:ack_seq', ack_seq, "expect_seq", expect_seq)
                print(self.who," SEND WINDOW: ", ack_seq)
                senderReceivedACKSet[ack_seq] = 1     # 记录收到的ACK
                print(self.who," 收到ACK:",ack_seq,'并记录')
                if (self.send_base == (ack_seq + 1) % 256):
                    # 收到重复确认, 此处应当立即重发
                    pass
                    #self.window_size += 1

                if(ack_seq == self.send_base):
                    print(self.who,' 收到ACK:',ack_seq)
                    while(senderReceivedACKSet[self.send_base] == 1):
                        self.send_base = (self.send_base + 1) % 256   # 窗口滑动
                        # self.send_base = max(self.send_base, (ack_seq + 1) % 256)  ##窗口滑动
                    if(self.window_size < 7):                                   # 拥塞控制
                        self.window_size += 2
                        print(self.who,' 发送窗口+2，现在为：',self.window_size)
                    elif(self.window_size >=7 and self.window_size <10):         # 拥塞控制
                        self.window_size += 1
                        print(self.who, ' 发送窗口+1，现在为：', self.window_size)
                    print(self.who,' 当前窗口 send_base = ',self.send_base)
                if self.send_base == self.next_seq:  # 已发送分组确认完毕

                    self.sender_socket.settimeout(None)
                    return True

            except socket.timeout:
                # 超时，重发分组.              ## 选择重传
                print(self.who,' Sender wait for ACK timeout.')
                # for i in range(self.send_base, self.next_seq):
                #     print('Sender resend packet:', i)
                #     self.udp_send(self.packets[i])
                for i in range(self.send_base,self.send_base + self.window_size):
                    if(senderSentSet[i] == 1 and senderReceivedACKSet[i] == 0):
                        print(self.who,' Sender resend packet:', i)
                        self.udp_send(self.packets[i])
                self.window_size = 1
                print(self.who,' 线路拥塞,发送窗口减小为1！')                   #拥塞控制
                self.sender_socket.settimeout(self.timeout)  # reset timer
                count += 1
        return False




class GBNReceiver:
    def __init__(self, receiverSocket, who,timeout=10, lossRate=0,windowSize = WINDOW_SIZE+7):
        self.receiver_socket = receiverSocket
        self.timeout = timeout
        self.loss_rate = lossRate
        self.window_size = windowSize
        self.expect_seq = 0
        self.target = None
        self.who = who

    def udp_send(self, pkt):
        if self.loss_rate == 0 or random.randint(0, 1 / self.loss_rate) != 1:
            self.receiver_socket.sendto(pkt, self.target)
            print(self.who,' Receiver send ACK:', pkt[0])
        else:
            print(self.who,' Receiver send ACK:', pkt[0], ', but lost.')

    def wait_data(self):
        """
        接收方等待接受数据包
        """
        self.receiver_socket.settimeout(self.timeout)

        while True:
            try:
                data, address = self.receiver_socket.recvfrom(BUFFER_SIZE)
                self.target = address

                seq_num, flag, checksum, data = self.analyse_pkt(data)
                print(self.who,' Receiver receive packet:', seq_num)
                # 收到期望数据包且未出错
                if seq_num == self.expect_seq and getChecksum(data) == checksum:
                    self.expect_seq = (self.expect_seq + 1) % 256
                    ack_pkt = self.make_pkt(seq_num, seq_num)
                    self.udp_send(ack_pkt)
                    if flag:    # 最后一个数据包
                        return data, True    #向上层递交数据块
                    else:
                        return data, False
                else:
                    ack_pkt = self.make_pkt((self.expect_seq - 1) % 256, self.expect_seq)   #重复确认，让客户回退N步重传
                    self.udp_send(ack_pkt)
                    return bytes('', encoding='utf-8'), False

            except socket.timeout:
                return bytes('', encoding='utf-8'), False

    def analyse_pkt(self, pkt):
        '''
        分析数据包
        '''
        # if len(pkt) < 4:
        # print 'Invalid Packet'
        # return False
        seq_num = pkt[0]
        flag = pkt[1]
        checksum = pkt[2]
        data = pkt[3:]
        if flag == 0:
            print(self.who," seq_num: ",seq_num, "not end ")
        else:
            print(self.who," seq_num: ", seq_num, " end ")
        return seq_num, flag, checksum, data

    def make_pkt(self, ackSeq, expectSeq):
        """
        创建ACK确认报文
        """
        return struct.pack('BB', ackSeq, expectSeq)

    def wait_data_SR(self,receiverReceivedSet,buffer):
        """
        接收方等待接受数据包
        """
        ##下面的写到主函数里
        # receiverReceivedSet = []
        # buffer = []
        self.receiver_socket.settimeout(self.timeout)

        while True:
            try:
                data, address = self.receiver_socket.recvfrom(BUFFER_SIZE)
                self.target = address

                seq_num, flag, checksum, data = self.analyse_pkt(data)
                print(self.who,' Receiver receive packet:', seq_num)
                receiverReceivedSet[seq_num] = 1
                # 收到期望数据包且未出错
                if seq_num == self.expect_seq and getChecksum(data) == checksum:
                    self.expect_seq = (self.expect_seq + 1) % 256
                    ack_pkt = self.make_pkt(seq_num, seq_num)
                    self.udp_send(ack_pkt)

                    for i in range(self.expect_seq, self.expect_seq + self.window_size):
                        if(receiverReceivedSet[i] == 1):
                            self.expect_seq = (self.expect_seq + 1) % 256
                            data = data + buffer[i]
                        else:
                            break
                    if flag:  # 最后一个数据包
                        return data, True  # 向上层递交数据块
                    else:
                        return data, False

                elif(seq_num > self.expect_seq and seq_num <self.expect_seq+self.window_size and getChecksum(data) == checksum):
                    if(flag == 0):
                        receiverReceivedSet[seq_num] = 1         # 记录已经收到
                        buffer[seq_num] = data
                        ack_pkt = self.make_pkt(seq_num, seq_num)
                        self.udp_send(ack_pkt)
                    else:
                        receiverReceivedSet[seq_num] = 0         # 若是最后一个包未按序到达，则丢弃并标记为未接受过
                    return bytes('', encoding='utf-8'), False
                elif(seq_num < self.expect_seq):
                    ack_pkt = self.make_pkt(seq_num, seq_num)
                    self.udp_send(ack_pkt)
                    return bytes('', encoding='utf-8'), False
                else:
                    return bytes('', encoding='utf-8'), False


            except socket.timeout:
                return bytes('', encoding='utf-8'), False



##########
# 下面写封装的发送函数和接收函数
def ReceiveProcess(receiver, fp,who):
    reset = False
    while True:
        data, reset = receiver.wait_data()
        print(who,' Data length:',len(data))
        fp.write(data)
        if reset:
            receiver.expect_seq = 0
            fp.close()
            break

def SendProcess(sender,fp,who):
    dataList = []
    while True:                       # 把文件夹下的数据提取出来
        data = fp.read(2048)
        if len(data) <= 0:
            break
        dataList.append(data)
    print(who,' The total number of data packets: ', len(dataList))

    pointer = 0
    while True:
        while sender.next_seq < (sender.send_base + sender.window_size):
            if pointer >= len(dataList):
                break
            #发送窗口为被占满
            data = dataList[pointer]

            checksum = getChecksum(data)

            if pointer < len(dataList) - 1:
                sender.packets[sender.next_seq] = sender.make_pkt(sender.next_seq, data, checksum,
                                                                  stop=False)
            else:
                sender.packets[sender.next_seq] = sender.make_pkt(sender.next_seq, data, checksum,
                                                                  stop=True)
            print(who,' Sender send packet:', pointer)
            sender.udp_send(sender.packets[sender.next_seq])
            sender.next_seq = (sender.next_seq + 1) % 256
            pointer += 1
        flag = sender.wait_ack()
        if pointer >= len(dataList):
            break
    fp.close()




def SendProcess_SR(sender,fp,who):
    senderSendSet = []
    senderReceivedACKSet = []
    dataList = []
    while True:                       # 把文件夹下的数据读取出来
        data = fp.read(2048)
        if len(data) <= 0:
            break
        dataList.append(data)
    print(who,' The total number of data packets: ', len(dataList))

    # #放到主函数里去做
    for i in range(0, 100000):
        senderSendSet.append(0)         # 初始设置已发送记录全为零
        senderReceivedACKSet.append(0)  # 初始设置已接收ACK记录全为零

    pointer = 0
    while True:
        while sender.next_seq < (sender.send_base + sender.window_size) and senderSendSet[sender.next_seq] == 0:
            if pointer >= len(dataList):
                break
            # 发送窗口为被占满
            data = dataList[pointer]

            checksum = getChecksum(data)

            if pointer < len(dataList) - 1:
                sender.packets[sender.next_seq] = sender.make_pkt(sender.next_seq, data, checksum,
                                                                  stop=False)
            else:
                sender.packets[sender.next_seq] = sender.make_pkt(sender.next_seq, data, checksum,
                                                                  stop=True)
            print(who,' Sender send packet:', pointer)
            sender.udp_send(sender.packets[sender.next_seq])
            senderSendSet[sender.next_seq] = 1                          # 记录已发送的分组编号
            sender.next_seq = (sender.next_seq + 1) % 256
            pointer += 1
        flag = sender.wait_ack_SR(senderSendSet, senderReceivedACKSet)
        if pointer >= len(dataList):
            break
    fp.close()


def ReceiveProcess_SR(receiver, fp, who):
    reset = False
    receiverReceivedSet = []   # 用于记录接收到的分组
    buffer = []
    for i in range(0,1000):
        receiverReceivedSet.append(0)
        buffer.append('')

    while True:
        data, reset = receiver.wait_data_SR(receiverReceivedSet,buffer)
        print(who,' Data length:',len(data))
        fp.write(data)
        if reset:
            receiver.expect_seq = 0
            fp.close()
            break
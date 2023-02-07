# -*- coding: utf-8 -*-
# @Author  : hombin
# @Time    : 2022/2/2 02:22
# @File    : http_proxy.py
# @Desc    : https://github.com/wengchaoxi/simple-http-proxy/blob/main/simple_http_proxy.py

import socket
import select
import time


def debug(tag, msg):
    """格式化输出"""
    print('[%s] %s' % (tag, msg))


class HttpRequestPacket(object):
    """
    HTTP 请求包
    """

    def __init__(self, data):
        self.__parse(data)

    def __parse(self, data):
        """
        解析一个HTTP请求数据包
        GET http://test.wengcx.top/index.html HTTP/1.1\r\nHost: test.wengcx.top\r\nProxy-Connection: keep-alive\r\nCache-Control: max-age=0\r\n\r\n

        参数：data 原始数据
        """
        i0 = data.find(b'\r\n')  # 请求行与请求头的分隔位置
        i1 = data.find(b'\r\n\r\n')  # 请求头与请求数据的分隔位置

        # 请求行 Request-Line
        self.req_line = data[:i0]
        self.method, self.req_uri, self.version = self.req_line.split()  # 请求行由 method、request uri、version 组成

        # 请求头域 Request Header Fields
        self.req_header = data[i0 + 2:i1]
        self.headers = {}
        for header in self.req_header.split(b'\r\n'):
            k, v = header.split(b': ')
            self.headers[k] = v
        self.host = self.headers.get(b'Host')

        # 请求数据
        self.req_data = data[i1 + 4:]


class SimpleHttpProxy(object):
    """
    简单的 HTTP 代理
    客户端(client) <=> 代理端(proxy) <=> 服务端(server)
    """

    def __init__(self, host='0.0.0.0', port=8080, listen=10, bufsize=8, delay=1):
        """
        初始化代理套接字，用于与客户端、服务端通信
        参数：host 监听地址，默认0.0.0.0，代表本机任意ipv4地址
        参数：port 监听端口，默认8080
        参数：listen 监听客户端数量，默认10
        参数：bufsize 数据传输缓冲区大小，单位kb，默认8kb
        参数：delay 数据转发延迟，单位ms，默认1ms
        """
        self.socket_proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 将 SO_REUSEADDR 标记为True, 当 socket 关闭后，立刻回收该 socket 的端口
        self.socket_proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_proxy.bind((host, port))
        self.socket_proxy.listen(listen)

        self.socket_recv_bufsize = bufsize * 1024
        self.delay = delay / 1000.0

        debug('info', 'bind=%s:%s' % (host, port))
        debug('info', 'listen=%s' % listen)
        debug('info', 'bufsize=%skb, delay=%sms' % (bufsize, delay))

    def __del__(self):
        self.socket_proxy.close()

    @staticmethod
    def __connect(host, port):
        """
        解析 DNS 得到 套接字地址 并与之建立连接
        :param host: 主机
        :param port: 端口
        :return: 与目标主机建立连接的 套接字
        """
        # 解析 DNS 获取对应协议簇、socket 类型、目标地址
        # getaddrinfo -> [(family, sockettype, proto, canonname, target_addr),]
        (family, sockettype, _, _, target_addr) = socket.getaddrinfo(host, port)[0]

        tmp_socket = socket.socket(family, sockettype)
        tmp_socket.setblocking(False)
        tmp_socket.settimeout(5)
        tmp_socket.connect(target_addr)
        return tmp_socket

    def __proxy(self, socket_client):
        """
        代理核心程序
        参数：socket_client 代理端与客户端之间建立的套接字
        """
        # 接收 客户端请求数据
        req_data = socket_client.recv(self.socket_recv_bufsize)
        if req_data == b'':
            return

        # 解析 http 请求数据
        http_packet = HttpRequestPacket(req_data)

        # 获取服务端 host、port
        if b':' in http_packet.host:
            server_host, server_port = http_packet.host.split(b':')
        else:
            server_host, server_port = http_packet.host, 80

        # 修正 http 请求数据
        tmp = b'%s//%s' % (http_packet.req_uri.split(b'//')[0], http_packet.host)
        req_data = req_data.replace(tmp, b'')

        # HTTP
        if http_packet.method in [b'GET', b'POST', b'PUT', b'DELETE', b'HEAD']:
            socket_server = self.__connect(server_host, server_port)  # 建立连接
            socket_server.send(req_data)  # 将 客户端请求数据 发给 服务端

        # HTTPS，会先通过 CONNECT 方法 建立 TCP 连接
        elif http_packet.method == b'CONNECT':
            socket_server = self.__connect(server_host, server_port)  # 建立连接

            success_msg = b'%s %d Connection Established\r\nConnection: close\r\n\r\n' % (http_packet.version, 200)
            socket_client.send(success_msg)  # 完成连接，通知客户端

            # 客户端得知连接建立，会将真实请求数据发送给代理服务端
            req_data = socket_client.recv(self.socket_recv_bufsize)  # 接收客户端真实数据
            socket_server.send(req_data)  # 将客户端真实请求数据发给服务端

        # 使用 select 异步处理，不阻塞
        self.__nonblocking(socket_client, socket_server)

    def __nonblocking(self, socket_client, socket_server):
        """
        使用 select 实现 异步处理数据
        参数：socket_client 代理端 与 客户端 之间建立的 套接字
        参数：socket_server 代理端 与 服务端 之间建立的 套接字
        """
        _rlist = [socket_client, socket_server]
        is_recv = True
        while is_recv:
            try:
                # rlist, wlist, elist = select.select(_rlist, _wlist, _elist, [timeout])
                # 参数1：当列表 _rlist 中的文件描述符fd 状态为readable时，fd 将被添加到 rlist
                # 参数2：当列表 _wlist 中存在文件描述符fd 时，fd 将被添加到 wlist
                # 参数3：当列表 _xlist 中的文件描述符fd 发生错误时，fd 将被添加到 elist
                # 参数4：超时时间 timeout
                #  1) 当 timeout==None 时，select 将一直阻塞，直到监听的 文件描述符fd 发生变化时返回
                #  2) 当 timeout==0 时，select 不会阻塞，无论 文件描述符fd 是否有变化，都立刻返回
                #  3) 当 timeout>0 时，若 文件描述符fd 无变化，select 将被阻塞 timeout 秒再返回
                rlist, _, elist = select.select(_rlist, [], [], 2)
                if elist:
                    break
                for tmp_socket in rlist:
                    is_recv = True
                    # 接收数据
                    data = tmp_socket.recv(self.socket_recv_bufsize)
                    if data == b'':
                        is_recv = False
                        continue

                    # socket_client 状态为 readable, 当前接收的数据来自 客户端
                    if tmp_socket is socket_client:
                        socket_server.send(data)  # 将 客户端请求数据 发往 服务端
                        # debug('proxy', 'client -> server')

                    # socket_server 状态为 readable, 当前接收的数据 来自 服务端
                    elif tmp_socket is socket_server:
                        socket_client.send(data)  # 将 服务端响应数据 发往 客户端
                        # debug('proxy', 'client <- server')

                time.sleep(self.delay)  # 适当延迟以降低 CPU 占用
            except Exception as e:
                debug("select", e)
                break

        socket_client.close()
        socket_server.close()

    def client_socket_accept(self):
        """
        获取 已经与代理端建立连接的 客户端套接字，如无则阻塞，直到可以获取一个建立连接套接字
        返回：socket_client 代理端与客户端之间建立的套接字
        """
        socket_client, _ = self.socket_proxy.accept()
        return socket_client

    def handle_client_request(self, socket_client):
        try:
            self.__proxy(socket_client)
        except Exception as e:
            debug("client", e)

    def start(self):
        try:
            import _thread as thread  # py3
        except ImportError:
            import thread  # py2
        while True:
            try:
                # self.handle_client_request(self.client_socket_accept())
                thread.start_new_thread(self.handle_client_request, (self.client_socket_accept(),))
            except KeyboardInterrupt:
                break


if __name__ == '__main__':
    import sys
    import getopt

    # 默认参数
    _host, _port, _listen, _bufsize, _delay = '0.0.0.0', 8080, 10, 8, 1

    # 获取 命令行 参数
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'h:p:l:b:d:', ['host=', 'port=', 'listen=', 'bufsize=', 'delay='])
        for opt, arg in opts:
            if opt in ('-h', '--host'):
                _host = arg
            elif opt in ('-p', '--port'):
                _port = int(arg)
            elif opt in ('-l', '--listen'):
                _listen = int(arg)
            elif opt in ('-b', '--bufsize'):
                _bufsize = int(arg)
            elif opt in ('-d', '--delay'):
                _delay = float(arg)

            # 复杂度增加
            # host = arg if opt in ("-h", "--host") else '0.0.0.0'
            # port = int(arg) if opt in ("-p", "--port") else 8080
            # listen = int(arg) if opt in ("-l", "--listen") else 10
            # bufsize = int(arg) if opt in ("-b", "--bufsize") else 8
            # delay = float(arg) if opt in ("-d", "--delay") else 1

    except Exception as e:
        debug("ERROR", e.args[0])
        debug('error', 'read the readme.md first!')
        sys.exit()

    # 启动代理
    SimpleHttpProxy(_host, _port, _listen, _bufsize, _delay).start()


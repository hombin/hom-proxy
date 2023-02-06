# hom-proxy
A simple proxy service.

### 运行参数
```shell
-h, --host 指定代理主机地址，默认 0.0.0.0，代表本机任意 ipv4 地址
-p, --port 指定代理主机端口，默认 8080
-l, --listen 指定监听客户端数量，默认 10
-b, --bufsize 指定数据传输缓冲区大小，值为整型，单位 kb，默认 8
-d, --delay 指定数据转发延迟，值为浮点型，单位 ms，默认 1
```

### 服务启动
```shell
# 启动服务
[hombin@localhost ~]$ python simple_http_proxy.py --bufsize 64
[info] bind=0.0.0.0:8080
[info] listen=10
[info] bufsize=64kb, delay=1ms

# 注：Linux 查看本机 IP地址 的命令为 ifconfig，Windows 为 ipconfig
```

### 使用配置
```markdown
客户端
1. 电脑：打开网络和Internet设置 -> 代理 -> 手动设置代理 -> 配置代理服务器IP和端口号
2. 手机：选择一个已连接的WIFI，修改该网络 -> 显示高级选项 -> 手动设置代理 -> 配置代理服务器IP和端口号
```

### TODO
- [ ] 抽离配置项
- [ ] 文件服务


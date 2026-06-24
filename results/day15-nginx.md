# Nginx

好的，我们从头开始，系统地学习 Nginx。这里不罗列零散的配置片段，而是从 **“为什么需要它”**、**“它是什么”**、**“它怎么工作”** 到 **“如何配置它”**，帮你建立一个完整的知识框架。

---

## 第一部分：为什么需要 Nginx？（定位）

在你之前学习的 FastAPI + Uvicorn 组合中，Uvicorn 本身就是一个 Web 服务器，可以直接对外提供服务。那为什么生产环境还要在前面加一个 Nginx？

| 场景                          | 只有 Uvicorn                           | Uvicorn + Nginx                                  |
| :---------------------------- | :------------------------------------- | :----------------------------------------------- |
| **并发静态文件**（图片、CSS） | 占用应用进程处理，浪费算力             | Nginx 直接返回，极快且不占用应用资源             |
| **HTTPS 加密**                | 需要在 Python 代码里配置证书，重启麻烦 | 在 Nginx 层统一管理证书，重启 Nginx 即可         |
| **负载均衡**                  | 单机单进程，无法扩展                   | Nginx 可将请求分发到多个 Uvicorn 实例            |
| **安全防护**                  | 需要自己写中间件                       | Nginx 提供限流、IP 黑名单等现成功能              |
| **流式响应**（SSE/WebSocket） | 需要应用层处理长连接                   | Nginx 长连接管理更成熟，但需特殊配置（关闭缓冲） |

**一句话总结：Nginx 是 Web 应用的“门卫”+“快递分拣中心”，负责接收所有请求，并决定是自己处理（静态文件/缓存），还是转发给后端的某个应用服务器。**

---

## 第二部分：Nginx 是什么？（核心架构）

### 2.1 它是什么

Nginx 是一个**高性能的 HTTP 服务器和反向代理服务器**。

- **HTTP 服务器**：能直接处理 HTTP 请求，返回文件或动态内容。
- **反向代理服务器**：接收客户端请求，将其转发给一个或多个后端服务器，并将响应返回给客户端。

### 2.2 它的核心设计：事件驱动 + 异步非阻塞

这是 Nginx 高性能的根本原因，也是它与传统 Web 服务器（如 Apache）的最大区别。

**传统 Apache（进程/线程模型）**：
每个连接分配一个进程或线程，连接数一多（如 1 万并发），就需要 1 万个进程/线程，内存和上下文切换开销巨大。

**Nginx（事件驱动模型）**：
一个 Worker 进程使用 **事件循环（Event Loop）** 来处理成千上万个连接。当连接没有数据可读/写时，Worker 不会阻塞等待，而是去处理其他连接。数据到达时，通过事件通知 Worker 来读取。

**架构图**：

```
                Master 进程（管理员）
               /       |        \
          Worker1  Worker2  WorkerN （工作进程）
         /  |  \    /  |  \    /  |  \
      连接1 连接2 ... 连接10000 ...
```

- **Master 进程**：负责读取配置、绑定端口、管理 Worker 进程（启动/停止/热重载）。不处理请求。
- **Worker 进程**：实际处理请求。数量通常等于 CPU 核心数。

---

## 第三部分：Nginx 配置文件（核心语法）

这是学习 Nginx 最关键的部分。配置文件通常是 `/etc/nginx/nginx.conf`。

### 3.1 配置文件的层次结构

```
main 块（全局配置）
├── events 块（事件驱动配置）
└── http 块（HTTP 核心配置）
    ├── upstream 块（定义后端服务器组）
    ├── server 块（定义一个虚拟主机/站点）
    │   ├── listen 指令
    │   ├── server_name 指令
    │   └── location 块（URL 路由规则）
    │       ├── proxy_pass 指令
    │       ├── root 指令
    │       └── 更多指令...
    └── server 块（可以有多个）
```

### 3.2 指令类型

- **简单指令**：`name value;`（以分号结尾）
- **块指令**：`name { ... }`（包含在花括号内）

### 3.3 上下文（Context）

配置指令必须放在特定的块内才有效。

| 上下文     | 作用范围                      |
| :--------- | :---------------------------- |
| `main`     | 全局，所有其他块之外          |
| `events`   | 影响网络连接处理方式          |
| `http`     | 所有 HTTP 相关的配置          |
| `server`   | 定义虚拟主机（一个域名或 IP） |
| `location` | 匹配特定 URL 路径             |

---

## 第四部分：核心配置指令详解

### 4.1 main 上下文

```nginx
# 以哪个用户运行 Worker 进程
user www-data;

# Worker 进程数量（通常等于 CPU 核心数）
worker_processes auto;

# 错误日志路径和级别（debug/info/notice/warn/error/crit）
error_log /var/log/nginx/error.log warn;

# 主进程 PID 文件
pid /run/nginx.pid;
```

### 4.2 events 上下文

```nginx
events {
    # 每个 Worker 进程的最大并发连接数
    worker_connections 1024;

    # 使用 epoll（Linux 下高性能事件模型）
    use epoll;

    # 允许每个 Worker 同时接受多个连接
    multi_accept on;
}
```

### 4.3 http 上下文

```nginx
http {
    # 基础配置
    include /etc/nginx/mime.types;        # 文件类型映射
    default_type application/octet-stream; # 默认 MIME 类型

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;          # 启用高效文件传输
    tcp_nopush on;        # 优化数据包发送
    tcp_nodelay on;       # 禁用 Nagle 算法（适合小数据包）
    keepalive_timeout 65; # Keep-Alive 超时时间
    gzip on;              # 启用压缩
    gzip_types text/plain text/css application/json;

    # 上游服务器组（负载均衡）
    upstream app_backend {
        server 127.0.0.1:8000;
        server 127.0.0.1:8001;
        server 127.0.0.1:8002;
        # 负载均衡算法：默认轮询，可配置 least_conn / ip_hash
    }

    # 第一个虚拟主机
    server {
        listen 80;
        server_name example.com;

        location / {
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### 4.4 server 上下文（虚拟主机）

```nginx
server {
    listen 80;                      # 监听端口
    server_name example.com;        # 域名（支持通配符 *.example.com）

    # 根目录（静态文件）
    root /var/www/html;
    index index.html index.htm;

    # 错误页面
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}
```

### 4.5 location 上下文（URL 路由）

`location` 是 Nginx 配置中最核心、最灵活的部分，用于匹配请求的 URL。

```nginx
location / {
    # 匹配所有以 / 开头的请求
}

location /api/ {
    # 匹配以 /api/ 开头的请求（如 /api/users）
}

location ~ \.php$ {
    # 使用正则表达式：匹配以 .php 结尾的请求
}

location = / {
    # 精确匹配：只匹配根路径 /
}
```

**匹配优先级**：

1. `=` 精确匹配（最高）
2. `^~` 前缀匹配（不检查正则）
3. `~` 或 `~*` 正则匹配（按配置顺序）
4. 普通前缀匹配（最长匹配优先）

```nginx
# 示例：FastAPI + 静态文件分离
server {
    listen 80;
    server_name myapp.com;

    # 静态文件直接由 Nginx 处理
    location /static/ {
        alias /var/www/myapp/static/;
        expires 30d;  # 缓存 30 天
    }

    # 动态 API 转发给 Uvicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 前端应用（单页应用）统一入口
    location / {
        root /var/www/myapp/dist;
        try_files $uri $uri/ /index.html;  # 支持前端路由
    }
}
```

---

## 第五部分：反向代理与负载均衡（重点）

### 5.1 反向代理配置

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;  # 后端地址

    # 必备：传递原始请求信息
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 超时控制
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

### 5.2 负载均衡

```nginx
upstream my_backend {
    # 默认轮询
    server 127.0.0.1:8000 weight=3;  # 权重 3（接收更多流量）
    server 127.0.0.1:8001;
    server 127.0.0.1:8002 backup;   # 备用服务器（其他都挂了才启用）

    # 其他负载均衡算法：
    # least_conn;    # 最少连接
    # ip_hash;       # 基于 IP 哈希（保证同一用户始终访问同一服务器）
}

server {
    location / {
        proxy_pass http://my_backend;
    }
}
```

### 5.3 流式响应（SSE/WebSocket）的特殊配置

对于 AI 逐字输出或 WebSocket，Nginx 默认会缓冲响应，必须关闭：

```nginx
location /chat/stream {
    proxy_pass http://app_backend;

    # 关键配置：禁用缓冲
    proxy_buffering off;
    proxy_cache off;

    # WebSocket 支持
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

---

## 第六部分：实际部署步骤

### 6.1 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# 启动
sudo systemctl start nginx
sudo systemctl enable nginx  # 开机自启
```

### 6.2 配置文件结构（Ubuntu/Debian）

```
/etc/nginx/
├── nginx.conf          # 主配置文件
├── sites-available/    # 所有站点配置（可用）
│   └── myapp.conf
├── sites-enabled/      # 已启用的站点（软链接到 sites-available）
│   └── myapp.conf -> ../sites-available/myapp.conf
└── conf.d/             # 额外的配置文件
```

### 6.3 启用站点

```bash
# 1. 创建配置文件
sudo nano /etc/nginx/sites-available/myapp

# 2. 创建软链接启用
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/

# 3. 测试配置语法
sudo nginx -t

# 4. 重新加载（不中断服务）
sudo nginx -s reload

# 或重启
sudo systemctl restart nginx
```

---

## 第七部分：日志与调试

### 7.1 日志路径

- 访问日志：`/var/log/nginx/access.log`
- 错误日志：`/var/log/nginx/error.log`

### 7.2 实时查看日志

```bash
sudo tail -f /var/log/nginx/access.log
```

### 7.3 自定义日志格式

```nginx
log_format custom '$remote_addr - $remote_user [$time_local] "$request" '
                  '$status $body_bytes_sent "$http_referer" '
                  '"$http_user_agent" "$http_x_forwarded_for"';
access_log /var/log/nginx/access.log custom;
```

### 7.4 常见错误排查

- **502 Bad Gateway**：后端应用未启动或挂了。
- **404 Not Found**：路径配置错误或文件不存在。
- **403 Forbidden**：权限问题（Nginx 用户无法读取文件）。
- **404 且静态文件路径对**：检查 `root` 和 `alias` 的区别（`root` 会拼接完整路径，`alias` 会替换 location 部分）。

---

## 第八部分：性能优化建议

| 配置项                 | 建议值               | 说明                     |
| :--------------------- | :------------------- | :----------------------- |
| `worker_processes`     | `auto`               | 自动等于 CPU 核心数      |
| `worker_connections`   | 1024~2048            | 每个 Worker 的最大连接数 |
| `worker_rlimit_nofile` | 20000                | 操作系统文件描述符限制   |
| `keepalive_timeout`    | 30~65                | 保持长连接，减少握手开销 |
| `gzip on`              | 开启                 | 压缩响应，减少带宽       |
| `sendfile on`          | 开启                 | 零拷贝传输静态文件       |
| `proxy_buffering off`  | **流式响应必须关闭** | 否则 AI 逐字输出会失效   |

---

## 第九部分：学习路径建议

1. **先理解概念**：反向代理、负载均衡、虚拟主机。
2. **动手安装 + 基础配置**：搞一个简单的静态网站（`root` + `index`）。
3. **配置反向代理**：将请求转发到 FastAPI 应用（`proxy_pass`）。
4. **负载均衡**：启动 2~3 个 Uvicorn 实例，用 `upstream` 分发请求。
5. **HTTPS**：用 Let's Encrypt 配置证书。
6. **流式响应**：配置 AI 聊天应用的 SSE（关闭缓冲）。
7. **日志与监控**：理解 `access.log` 和 `error.log`。

---

Nginx 的配置文件可以非常复杂，但 90% 的生产场景都离不开我上面讲解的这几十条核心指令。建议你从一个小项目开始，先把**反向代理 + 静态文件处理**跑通，再逐步深入负载均衡和 HTTPS。

如果你卡在某个具体配置上（比如 `alias` 和 `root` 的区别，或者 WebSocket 代理报错），可以随时发配置给我，我帮你分析。

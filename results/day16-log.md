# logging

`logging` 是 Python 标准库中的日志记录模块。它与 `print()` 最本质的区别在于：**`logging` 是为生产环境设计的**。它提供了日志级别、输出目标（控制台/文件/网络）、格式控制以及按模块分层管理的能力，是构建健壮后端系统的基石。

结合你之前学习的 FastAPI、Nginx 和 Gunicorn，今天重点讲解如何在**生产级 Python 项目**中正确使用 `logging`。

---

### 1. 核心组件（四大金刚）

理解 `logging` 模块，其实就是理解以下四个组件的协作关系：

| 组件                      | 作用                                         | 通俗类比                                           |
| :------------------------ | :------------------------------------------- | :------------------------------------------------- |
| **Logger（记录器）**      | 应用程序直接调用的入口。负责产生日志消息。   | 你（开发者），负责“说话”记录事情。                 |
| **Handler（处理器）**     | 决定日志消息的去向（输出到哪里）。           | 邮局，决定把信寄到本地（文件）还是外地（终端）。   |
| **Formatter（格式化器）** | 决定日志消息的最终显示格式。                 | 信封的排版样式，决定包含时间、级别还是只显示消息。 |
| **Filter（过滤器）**      | 提供更细粒度的控制，决定哪些日志可以被输出。 | 保安，根据规则拦截或放行日志。                     |

**工作流**：Logger 产生消息 → Filter 过滤 → 判断日志级别 → Formatter 格式化 → Handler 输出。

---

### 2. 日志级别（Log Levels）

日志级别是过滤的基础。标准库定义了 6 个级别：

| 级别       | 数值 | 使用场景                                               |
| :--------- | :--- | :----------------------------------------------------- |
| `DEBUG`    | 10   | 开发调试阶段，最详细的诊断信息。                       |
| `INFO`     | 20   | 确认程序按预期运行（如“用户登录成功”）。               |
| `WARNING`  | 30   | 表明有潜在问题，但不影响程序运行（如“磁盘空间不足”）。 |
| `ERROR`    | 40   | 因更严重的问题，程序部分功能受损。                     |
| `CRITICAL` | 50   | 严重错误，程序可能即将崩溃。                           |

**设置规则**：如果 Logger 设置为 `WARNING`，则 `DEBUG` 和 `INFO` 级别的日志将被忽略。

---

### 3. 如何配置（基础与进阶）

#### 方式一：快速配置 `basicConfig`（适合单文件脚本）

最简单的入门方式，直接在代码开头配置：

```python
import logging

logging.basicConfig(
    level=logging.INFO,                     # 设置全局级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 格式
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('app.log'),     # 输出到文件
        logging.StreamHandler()             # 输出到控制台
    ]
)

logging.info("应用启动了")
```

#### 方式二：`dictConfig` 生产级配置（强烈推荐）

在生产环境中，建议使用 `dictConfig` 或 `fileConfig` 进行集中配置，便于维护且支持更复杂的场景（如日志轮转）。

```python
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(process)d] %(levelname)s - %(name)s: %(message)s'
        },
        'json': {  # 结构化日志，便于 ELK 采集
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',  # 按大小轮转
            'level': 'INFO',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'default'
        },
        'time_rotating': {  # 按时间轮转（推荐）
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'INFO',
            'filename': 'logs/app.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'default'
        }
    },
    'loggers': {
        'uvicorn': {  # 控制 Uvicorn 日志
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'myapp': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    },
    'root': {  # 根日志器配置
        'level': 'WARNING',
        'handlers': ['console']
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

---

### 4. 在模块中的最佳实践（`getLogger`）

不要在代码中到处使用 `logging.info()`，这样会丢失模块信息。标准的做法是每个模块使用自己的 `Logger` 实例：

```python
# 文件：my_module.py
import logging

# 推荐使用 __name__，日志会显示为 "my_module"
logger = logging.getLogger(__name__)

def process_data():
    logger.info("开始处理数据...")
    try:
        # 业务逻辑
        pass
    except Exception as e:
        # 记得记录完整的堆栈信息
        logger.error("数据处理失败", exc_info=True)
```

**`exc_info=True` 的魔法**：它会自动将当前异常堆栈信息完整打印出来，是排查 Bug 的利器。千万不要自己用 `str(e)` 代替。

---

### 5. 在 FastAPI 中的集成实战

FastAPI 默认使用 Uvicorn 的日志配置。为了让你的应用日志格式与 Uvicorn 统一，最佳做法是**在启动时注入配置**。

```python
from fastapi import FastAPI
import logging

app = FastAPI()

# 配置日志（这里可以使用上面的 dictConfig）
logger = logging.getLogger("uvicorn.error")  # 复用 Uvicorn 的配置
# 或者 logger = logging.getLogger("myapp")

@app.on_event("startup")
async def startup_event():
    logger.info("应用启动完成，数据库连接池已初始化")

@app.get("/")
async def root():
    logger.info(f"收到根路径请求")
    return {"message": "Hello World"}

# 也可以自定义中间件记录请求耗时
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"请求开始: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"请求结束: {request.method} {request.url.path} - 状态码 {response.status_code}")
    return response
```

---

### 6. 痛点解决：日志重复打印

新手常遇到一个问题：在同时配置了 `console` 和 `file` Handler 时，控制台明明只应输出一次，结果却输出了两次。

**原因**：子 Logger 默认会向父 Logger（如 `root`）传播日志，如果父子都绑定了相同的 Handler，就会重复打印。

**解决方案**：

1. 在子 Logger 配置中设置 `"propagate": False`（推荐）。
2. 或者只给 `root` 绑定 Handler，子 Logger 不绑定任何 Handler，只设置 `level`。

---

### 7. 生产环境下的三个关键配置

1.  **TimedRotatingFileHandler（按天轮转）**：
    绝对不要使用无限增长的单一日志文件。配置按天或按大小自动切割（如 `RotatingFileHandler` 或 `TimedRotatingFileHandler`），并限制备份数量，防止磁盘写满。

2.  **结构化日志（JSON 格式）**：
    如果你的日志要接入 ELK、Splunk 或阿里云日志服务，纯文本难以解析。建议安装 `python-json-logger` 库，输出 JSON 格式日志：

    ```python
    # 安装：pip install python-json-logger
    from pythonjsonlogger import jsonlogger
    # 在 Formatter 中使用 JsonFormatter
    ```

3.  **异步日志处理（解决 I/O 阻塞）**：
    在高并发场景下，写磁盘 I/O 可能会成为瓶颈。可以使用 `QueueHandler` 和 `QueueListener` 将日志操作放入队列，由独立线程异步写入，避免阻塞主业务线程。

    ```python
    from logging.handlers import QueueHandler, QueueListener
    import queue

    log_queue = queue.Queue(-1)  # 无界队列
    handler = logging.handlers.TimedRotatingFileHandler(...)
    queue_handler = QueueHandler(log_queue)

    listener = QueueListener(log_queue, handler)
    listener.start()  # 应用启动时开启，关闭时 listener.stop()
    ```

---

### 💎 总结：好的日志实践应该是怎样的？

1. **永远用 `__name__` 定义 Logger**。
2. **区分级别**：开发阶段用 `DEBUG`，生产环境至少用 `INFO` 或 `WARNING`。
3. **记录上下文**：不要只记“失败了”，要记录“哪个用户、什么参数、哪一步失败了”（日志结构化）。
4. **利用 `exc_info=True`** 完整记录异常堆栈。
5. **配置轮转**，永远防止磁盘被写爆。

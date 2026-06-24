import redis

# 创建全局连接池（程序启动时初始化一次）
pool = redis.ConnectionPool(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=10,  # 最大连接数
    socket_timeout=5,  # 超时时间（秒）
)

# 每次使用时从池子中获取连接
r = redis.Redis(connection_pool=pool)

# String
r.set("name", "leo1", 100)
r.set("age", 10)
r.incr("age", 10)

# hash操作
r.hset("info", "name", "leo")
r.hget(
    "info",
    "name",
)

r.hset("info", mapping={"name": "Alice", "age": 30})
print(r.hgetall("info"))


# list 操作
r.delete("list")
r.lpush("list", 1, 2, 3)
print(r.lpop("list"))
r.linsert("list", "BEFORE", "2", "100")
print(r.lrange("list", 0, -1))

# set 操作
r.sadd("set", "leo", "leo1", "leo2")
print(r.smembers("set"))


## 有序集合

r.zadd("rank", mapping={"Alice": 100, "Bob": 90})
print(r.zrevrange("rank", 0, -1, withscores=True))
print(r.zrangebyscore("rank", 60, 100, start=0, num=12))

# redis

基于内存的键值型 NoSQL 数据库

## 特征

- 键值型
- 单线程，每个命令具备原子性
- 低延迟，速度快（基于内存，IO 多路复用，良好的编码）
- 支持数据持久化
- 支持主从集群，分片集群
- 支持多语言客户端

## 常见命令

### 数据结构

key ： string
value: 基本类型 + 特殊类型

**基本类型**：

- string
- Hash
- List
- Set
- SortedSet

**特殊类型**：

- GEO： {A: (120.1, 30.5)}
- BitMap: 0120111010
- HyperLog: 0110101010101

### 通用命令

- `KEYS` :查看所有的key
- `DEL`:删除
- `EXISTS`: 判断存在
- `EXPIRE`：设置一个有效期
- `TTL`: 查看剩余时间

### String 类型

这里包含了 number 和 float

- `SET`: 设置
- `GET`
- `MSET` : 批量设置
- `MGET`
- `incr` : 数值自增
- `incrby`: 按值去增加
- `incrbyfloat`: float
- `setnx`: 新增当 key不存在的时候
- `setex`: 设置key 并赋予时间

## key的层级

`项目名:业务名:类型:id`

### Hash类型

无序字典

- `HSET`: 需要指定 field
- `HGET`: 需要指定 field
- `hmset`
- `hmget`
- `hgetall`: get all
- `hkeys`: get all keys
- `hvals`: get all values
- `hincrby`
- `hsetnx`

### List 类型

类似于双向链表

- lpush : 列表左侧插入
- lpop： 移除并返回列表左侧第一个，没有则 返回nil
- rpush
- rpop
- lrange key start end: 返回一段角标内所有的
- blpop 和 brpop:与 lpop 和 rpop 类似，只不在没有元素时候等待指定时间，而不是直接返回 nil

### Set 类型

- 无序
- 元素不可重复
- 查找快
- 支持交集 并集 差集等功能

**常见命令**

- SADD： add
- SREM： remove
- scard： 返回元素的个数
- sismember key member: 判断一个元素是否在 Set 中
- smembers: 返回所有的元素
- sinter key1 key2 : 求key1与key2的交集
- sdiff : 差集
- sunion ： 并集

## SortedSet 类型

可排序的 Set 集合，通过添加时候的分数排序

**特性**

- 可排序
- 元素不重复
- 查询速度快

**常见命令**

- zadd key score member: 添加，存在更新 score
- zrem
- zscore key member: 获取 score 值
- zrank key member: 获取排名
- zcard: 个数
- zcount key min max: 统计区间内的元素个数, 分数
- zincrby key increment member: 指定步长增长
- zrange key min max: 排序后，获取元素, index
- zrangebyscore key min max: 按照分数返回
- zdiff, zinter, zunion: 差集， 交集， 并集

默认升序，降序的话 在 Z后面添加 REV

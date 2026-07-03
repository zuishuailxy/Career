import asyncio
import time


# 1. 定义一个协程函数
async def say_hello():
    print("Hello")
    await asyncio.sleep(1)  # 模拟一个耗时 I/O 操作
    print("World")


# 2. 运行协程
asyncio.run(say_hello())


async def say_after(delay, what):
    await asyncio.sleep(delay)
    print(what)


async def main():
    # 创建任务，让它们在后台并发执行

    task1 = asyncio.create_task(say_after(1, "Hello"))
    task2 = asyncio.create_task(say_after(2, "World"))

    print(f"开始时间: {time.strftime('%X')}")

    # 等待两个任务都完成
    await task1
    await task2

    print(f"结束时间: {time.strftime('%X')}")


asyncio.run(main())


async def main1():
    async with asyncio.TaskGroup() as tg:
        # 一个包含所有结果的列表 类似于promise.all
        # 在 TaskGroup 中，如果任何一个任务失败，其他任务会被自动取消，防止任务悬挂。
        task1 = tg.create_task(say_after(1, "Hello"))
        task2 = tg.create_task(say_after(2, "World"))
        # 等待两个任务都完成
        await task1
        await task2
    # 当 with 块结束时，会自动等待所有任务完成
    print("所有任务已完成")


asyncio.run(main1())


async def fetch_data(delay):
    await asyncio.sleep(delay)
    return f"数据在 {delay} 秒后返回"


async def main3():
    # 并发执行三个 fetch_data 协程，并按传入顺序返回结果
    # 如果任何一个任务抛出异常，gather 会取消其他任务并抛出该异常。设置 return_exceptions=True 可以让它返回异常对象而不是抛出
    results = await asyncio.gather(fetch_data(1), fetch_data(2), fetch_data(3))
    print(
        results
    )  # 输出: ['数据在 1 秒后返回', '数据在 2 秒后返回', '数据在 3 秒后返回']


asyncio.run(main3())

import threading
import time


# ============================================================
# 版本 1 — 基础累加（存在竞态条件，仅演示）
# ============================================================
def run_version1():
    count = 0

    def increment():
        nonlocal count
        for _ in range(100):
            tmp = count        # 读取
            time.sleep(0)      # ← 主动释放 GIL，放大竞态窗口
            tmp += 1
            count = tmp        # 写回

    threads = []
    for _ in range(1000):
        t = threading.Thread(target=increment)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()               # ✅ 等待所有线程完成

    print(f"版本1 (无锁)  最终 Count: {count:>7}  (期望 100000)")
    return count


# ============================================================
# 版本 2 — 带锁累加（修复后）
# ============================================================
def run_version2():
    count = 0
    lock = threading.Lock()

    def safe_increment():
        nonlocal count         # ✅ 声明 nonlocal（闭包中使用外层变量）
        for _ in range(100):
            with lock:
                count += 1

    threads = []
    for _ in range(1000):
        t = threading.Thread(target=safe_increment)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"版本2 (有锁)  最终 Count: {count:>7}  (期望 100000)")

    # 断言验证
    assert count == 100000, f"并发安全验证失败！count={count}"
    print("✅ 并发安全验证通过！")
    return count


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    ret1 = run_version1()
    ret2 = run_version2()

    # 预期：版本1 大概率不等于 100000（竞态），版本2 必定等于 100000
    print()
    if ret1 != 100000:
        print("⚠️  版本1 因竞态条件未达到预期值，符合预期（演示了并发安全问题）")
    else:
        print("ℹ️  版本1 恰好达到预期值（极端幸运，极少发生）")

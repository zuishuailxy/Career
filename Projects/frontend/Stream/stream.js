const prefix = "http://127.0.0.1:8000";

const fetchStream = async () => {
  console.log("start fetch");
  const response = await fetch(`${prefix}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: "讲个笑话",
    }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // 将当前数据块转为字符串
    buffer += decoder.decode(value, { stream: true });
    // 按换行符分割（SSE 规范中每个事件以 \n\n 结束，但简单场景可按 \n 分割）
    const lines = buffer.split("\n\n");
    // 保留最后一个可能不完整的部分
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith("data:")) {
        const data = line.slice(6); // 去掉 "data: "
        if (data === "[DONE]") {
          console.log("流结束");
          return;
        }

        // 渲染每个词或字
        console.log("收到:", data);
        // 例如追加到页面元素中
        document.getElementById("app").textContent += data;
      }
    }
  }
};

fetchStream();

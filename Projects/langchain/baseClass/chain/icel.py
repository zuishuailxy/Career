from utils import create_llm
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("讲个关于{topic}笑话")

llm = create_llm(1)

output_parser = StrOutputParser()

chain = prompt | llm | output_parser

result = chain.invoke({"topic": "程序员"})
print(result)

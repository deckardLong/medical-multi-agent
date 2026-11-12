from .graph import agent

if __name__ == "__main__":
    result = agent.invoke({"messages": [("user", "Triệu chứng của bệnh tiểu đường type 2 là gì?")]})
    print(result["messages"][-1].content)
"""存储层：SQLite（结构化） + Qdrant（向量）。

对外只暴露 repositories / retriever 的 DTO 接口，不泄露 SQL 与向量库实现细节。
"""

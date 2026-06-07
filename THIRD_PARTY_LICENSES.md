# 第三方许可与致谢

## 设计致谢

- **执行器接口/设计**:docker 执行器(每步一容器、共享工作卷、cleanup 必执行、防泄漏 labels)的接口与设计借鉴自 **GitLab Runner**(MIT License, © GitLab Inc.)。

## 运行时依赖

| 依赖 | 用途 | License |
|------|------|---------|
| docker (docker-py) | docker 执行器的 Python SDK | Apache-2.0 |
| minio | 分布式 worker 模式下的对象存储客户端 | Apache-2.0 |

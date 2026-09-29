"""手写业务实现层。

生成 router（apis/*_api.py）通过 pkgutil 扫描本包，装载继承
``apis/<tag>_api_base`` Base 类的实现子类并自动接线；未实现的端点由
生成基类兜底 500。第一个需求进门后，实现类落在本包各模块。
"""

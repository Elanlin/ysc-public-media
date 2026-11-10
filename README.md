# ysc-public-media

面向影视仓 / TVBox 兼容客户端的**合法开放媒体仓**。仓库不保存视频文件，只定时整理官方开放 API 返回的元数据和播放地址。

当前上游：

- [Internet Archive / Prelinger Archives](https://archive.org/details/prelinger)：只收录明确标注 Public Domain 或允许再分发的 Creative Commons 项目。
- [NASA Image and Video Library](https://images.nasa.gov/)：只读取 NASA 官方 API，并链接到 NASA 官方媒体文件。

## 导入地址

影视仓多仓地址：

```text
https://raw.githubusercontent.com/Elanlin/ysc-public-media/main/warehouse.json
```

如果客户端要求填写“配置地址”而不是“多仓地址”，使用：

```text
https://raw.githubusercontent.com/Elanlin/ysc-public-media/main/config.json
```

部分网络访问 `raw.githubusercontent.com` 较慢时，可以尝试 jsDelivr 镜像：

```text
https://cdn.jsdelivr.net/gh/Elanlin/ysc-public-media@main/warehouse.json
```

> 不同影视仓版本的菜单名称可能是“多仓管理”“配置管理”或“线路管理”。首次导入后如果目录为空，请先在 GitHub 的 Actions 页面手动运行一次 `Update open media catalog`。

## 工作方式

1. GitHub Actions 每天从开放上游获取目录。
2. `scripts/build_catalog.py` 校验来源、许可和播放文件类型，生成 `data/catalog.json`。
3. `spider/public_media.js` 在兼容客户端中提供分类、搜索、详情和直链播放。
4. 仓库只保存很小的 JSON/JS 文件，不需要额外购买服务器，也不保存片库。

## 内容与许可说明

- 本仓库中的代码采用 MIT License。
- 媒体文件不属于本仓库；每条内容保留原始来源、详情页和许可说明。
- NASA 内容通常不受美国版权保护，但 NASA 标识、人物肖像及第三方材料可能受额外规则约束，使用前应查看 [NASA Media Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)。
- 自动过滤只能降低风险，不能替代对单个条目授权状态的人工核验。

## 本地更新与校验

```bash
python scripts/build_catalog.py
python scripts/validate.py
python -m unittest discover -s tests
```

可通过环境变量调整条目数量：

```text
IA_LIMIT=12
NASA_LIMIT=10
```

## 目录结构

```text
config.json                           单线路配置
warehouse.json                        影视仓多仓入口
data/catalog.json                     自动生成的开放媒体目录
spider/public_media.js                影视仓 / TVBox JS Spider
scripts/build_catalog.py              上游聚合脚本
scripts/validate.py                   目录与配置校验
.github/workflows/update-catalog.yml  每日自动更新
```

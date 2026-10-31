# 徐州方言地图 · 地理边界数据

徐州 **10 个县级行政区**的边界轮廓（鼓楼 / 云龙 / 贾汪 / 泉山 / 铜山 / 丰县 / 沛县 / 睢宁 / 新沂 / 邳州）。

> 旧版 README 写的是「十三县区」，那是文档笔误：数据里一直是 10 个，也正是徐州全部的县级行政区。

## 谁是权威

| 文件 | 角色 | 顶点数 |
|---|---|---|
| `data/geo.full.js` | **权威版**，全局名 `window.XZ_GEO`，字段 `{name, adcode, label, polys}` | 1701 |
| `data/geo.lite.js` | 派生的精简版（RDP 降采样），全局名 `window.XZ_GEO_LITE` | 768 |
| `data/SHA256SUMS` | 两份产物的校验和 | — |

两者的 `polys` 嵌套层级一致（多边形 → 环 → 点），区县与 `adcode` 集合一致，只差顶点密度。
消费方是 [xuzhou-dialect-map](https://github.com/22258-cmd/xuzhou-dialect-map)，它加载的是权威版的副本
`data/geo.xuzhou.js`。

## 复现与自检

```bash
python tools/derive_lite.py            # 由 geo.full.js 生成 geo.lite.js 并更新 SHA256SUMS
python tools/derive_lite.py --check    # 只比对不写文件；产物被手改过就退出码 1
python tools/derive_lite.py --tol 0.006
```

零依赖（只用标准库）。`--check` 是给 CI 用的：改了一个顶点、或只改了派生物没重跑，都会当场报红。

> 旧脚本 `tools/build_geo.py` 已删除：它的输入是硬编码的 `D:\workbuddy\...\xz.json`（该目录已不存在），
> 输出路径也在仓库之外，任何人都跑不出本仓库的数据。

## 许可

代码（`tools/`、本 README）以 MIT 授权；**`data/` 下的边界数据来源待考，本项目不对其上游权利作任何担保，
也不据此授予任何许可** —— 详见 `NOTICE.md`。

# 网页采集工具

这是一个用于采集网页开区信息的Python脚本，可自动部署在GitHub上并通过GitHub Actions定期运行。

## 功能特点

- 采集指定网址的开区信息
- 自动去重相同时间开区的相同数据
- 将时间格式转换为时间戳（支持多种时间格式）
- 将采集结果保存为Markdown格式文件
- 可通过GitHub Actions自动定时运行

## 采集目标

- https://zhaosf.aitingshuchang.com/
- https://zhaosf.aitingshuchang.com/index2.html

## 时间格式处理

脚本支持处理以下三种时间格式：

1. `10月10日/13:00` → 转换为对应日期的时间戳
2. `今日14:00` → 转换为当天的时间戳
3. `★★精品全天推荐★★` → 保持原样不变

## 使用方法

### 本地运行

1. 确保已安装Python 3.6+
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 运行采集脚本：
   ```
   python scraper.py
   ```

> 注意：如果在Windows上运行提示'python'不是内部或外部命令，请尝试使用`python3`命令或者检查Python是否已正确安装并添加到系统PATH环境变量中。

### GitHub Actions自动运行

该项目配置了GitHub Actions工作流，会自动：

- 每天UTC时间0点（北京时间早上8点）运行采集任务
- 也可手动在GitHub仓库页面的Actions标签页中触发运行

采集结果会自动提交并推送到仓库中。

## 输出文件

采集结果保存在以下文件中：

1. `data/9pk.md` - Markdown格式的表格文件
2. `data/9pk_lines.txt` - 每行一条记录的文本文件，字段之间使用制表符分隔

### Markdown格式 (9pk.md)
- 服务器名称
- 服务器类型
- 开区时间（已转换为可读格式）
- 最低消费要求
- 服务器描述
- 特色功能

### 每行一条记录格式 (9pk_lines.txt)
- 每行包含一条完整的服务器信息
- 字段之间使用制表符(\t)分隔
- 时间字段保持时间戳格式（整数）

## 注意事项

- 请确保遵守目标网站的robots.txt规则和使用条款
- 过于频繁的请求可能会被目标网站屏蔽，请合理设置采集频率
- 如需修改采集目标或时间格式，可编辑 `scraper.py` 文件
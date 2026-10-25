# 全息元宝侦探 🔍

> 腾讯元宝搜索 API 比赛作品 ·「查得到，信得过 · 少点幻觉，多点搜索」
> 🕹️ 线上体验：https://truth-finder.app.workbuddy.host/?sharecode=6JADEZIVHE

输入一条传言，元宝侦探实时调元宝搜索全网爬证据，给出 **真 / 假 / 存疑** 判定 + 可点开的证据链。查不到就明说「不知道」，绝不编造。

## 核心特性

| 特性 | 说明 |
|------|------|
| 🔍 多轮真实搜索 | 后端调元宝搜索 SearchPro，多轮查询交叉比对，证据条数随查询动态变化 |
| 🕸️ 全息蜘蛛爬取动画 | 发送后蜘蛛从箭头出生，在居中带内追行爬取信息流，逐条点亮证据行 |
| 🃏 真假存疑判定 | 三态结论 + 每条证据带可信度评分与来源链接，可点开核对 |
| 🤷 敢说不知道 | 无足够证据时明确输出「不知道」徽章，拒绝幻觉编造 |
| 🎙️ 微信式麦克风 | 按住说话、松开自动识别并发送（SiliconFlow SenseVoice ASR，Key 只在服务端） |
| 📱 手机/桌面自适应 | 手机底部抽屉报告 + 蜘蛛按屏宽比例缩放；桌面右侧抽屉 + 剩余区居中 |

## 技术栈

- **后端**：Flask + 腾讯元宝搜索 SearchPro API（多轮搜索与交叉验证）+ SiliconFlow SenseVoice（ASR 转发）
- **前端**：原生 HTML/JS，Canvas 蜘蛛绘制，信息流滚动带引擎，零框架依赖
- **部署**：WorkBuddy Sites（单端口 HTTP 服务）

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 Key（复制模板并填入真实值）
cp .env.example .env   # Windows: copy .env.example .env
#   TENCENTCLOUD_WSA_APIKEY = 元宝搜索 Key
#   SILICONFLOW_KEY         = 硅基流动 Key（可选，麦克风识别用）

# 3. 启动
python app.py
# 打开 http://127.0.0.1:5050
```

环境变量也可以直接设置（部署平台推荐）：

```bash
export TENCENTCLOUD_WSA_APIKEY=sk-xxx
export SILICONFLOW_KEY=sk-xxx
```

## 项目结构

```
truth-finder/
├── app.py                  # Flask 后端：搜索/判定/ASR 转发
├── requirements.txt
├── .env.example            # Key 模板（真实 Key 走 .env / 环境变量）
└── templates/
    └── index.html          # 前端全部逻辑（蜘蛛动画/信息流/报告抽屉/麦克风）
```

## 演示截图

- 桌面端：蜘蛛居中带追行爬取 + 右侧报告抽屉
- 手机端：底部抽屉 + 按比例缩放的蜘蛛

（截图见 `crop-*.png` / `mob-*.png`）

## 比赛信息

- 赛题：🔍 侦探｜查得到，信得过 · 少点幻觉，多点搜索
- 截止：2026-10-25 23:59
- 交付：可打开的作品 + 3 次真实查询录屏（每次带来源）+ 公开发布

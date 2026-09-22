# EOS App

[中文](./README.md) | [English](./README.en.md)

**桌面端 AI 编码工作台。** 在一个窗口里完成对话协作、任务执行、命令验证与工程管理——适合真实项目，而不是只聊代码。

- 下载安装包：[Releases](https://github.com/eosaios/eos-app/releases)（始终以最新 Release 为准）
- 问题反馈：[Issues](https://github.com/eosaios/eos-app/issues)
- 终端版：[EOS CLI](https://github.com/eosaios/eos)

本仓库是 EOS App 的**官方发行仓**：提供安装包、版本说明与产品介绍，**不包含桌面端源码**。核心能力基于开源项目 [EOS CLI](https://github.com/eosaios/eos) 的 Rust 内核，安装包内附签名 Core（SHA-256 校验 + Ed25519 验签）。

## 为什么是 EOS App

写代码这件事，往往卡在工具切换上：对话在一个窗口，终端在另一个，浏览器再一个，Git 状态又要自己盯。

EOS App 把这些收进同一工作台：

- **说清需求，就能推进**——对话、计划、任务、审批串成一条线
- **AI 能上手操作网页**——内嵌实时浏览器，登录 / 验证时一键交还给你
- **改动看得见**——Git 状态、命令输出、产物预览就在旁边
- **长期用得顺**——主题皮肤、个性化回复、应用内更新、系统托盘

## 能力一览

**对话协作**  
对话工作区 · 计划 / 自动模式 · 审批与沙箱档位 · AI 优化表达 · 采集板（满意回复存成知识卡）

**任务与工程**  
任务中心与计划待办 · Bash 工作面 · Git 提交推送与提醒 · Worktree / 远程仓库 · 变更汇总与产物预览

**浏览器协作**  
内嵌实时浏览器（多标签、共享视口）· AI 导航 / 点选 / 填表 · 人工接管 · 选取元素引用进对话

**模型与上下文**  
多供应商模型接入 · 模型向导与连通测试 · 推理强度联动 · 实时上下文用量 · 规则 / 记忆 · 用量与费用

**扩展与外观**  
技能和应用 · 插件市场 · 自动化 · 官方主题皮肤 + 导入 / GitHub 安装 · MCP / LSP / 网络 / 通知

**桌面体验**  
应用内更新 · 系统托盘与单实例 · 桌面通知 · Windows / macOS / Linux 三端原生窗口

## 平台与安装

| 平台 | 架构 | 安装方式 |
|---|---|---|
| Windows | x64 | setup 安装器，或便携 zip |
| macOS | Intel / Apple Silicon | dmg 拖拽安装，或便携 tar.gz |
| Linux | amd64 / arm64 | tar.gz |

1. 打开 [Releases](https://github.com/eosaios/eos-app/releases)，下载对应平台的最新安装包
2. 需要时用同页的 `SHA256SUMS.txt` 校验
3. 安装后也可在应用内检查更新，自动下载安装

> 发行物命名以每个 Release 页资产列表为准，版本号随发版自动更新，不在本文重复维护。

## 界面预览

### 演示视频（90 秒）

[![EOS App 演示视频：从一句需求到可用的项目文件](https://eosaios.com/assets/eos-promo-preview.gif)](https://eosaios.com/assets/eos-promo.mp4)

点击预览观看完整演示——对话协作、任务执行与文件生成。

主工作台（macOS 为原生交通灯窗口；Windows / Linux 为对应平台风格）：

![EOS App 主工作台](https://github.com/eosaios/eos-app/releases/download/v1.0.0-beta.4/workspace-overview.png)

- 左侧：新对话、技能和应用、自动化，以及任务 / 工作树、用量 / 网络 / 记忆 / 帮助
- 中央：对话与主工作流
- 底部：发起新任务的输入区（可切换模型与推理强度），Bash 终端随附

## 许可证

安装包与文档采用 EOS App 非商用许可证（见 [LICENSE](./LICENSE)）：

- 个人 / 非商业用途可免费下载、安装与使用，并允许原样分发官方安装包与文档
- 禁止商业使用（含企业内部生产、收费服务、SaaS、二次商业分发）
- 商业使用须版权人单独书面授权
- 本仓库不提供桌面端源码

## 联系

- 问题反馈：https://github.com/eosaios/eos-app/issues
- 商业合作 / 授权咨询：legal@eosaios.com

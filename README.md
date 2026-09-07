# EOS App

[中文](./README.md) | [English](./README.en.md)

桌面端 AI 编码工作台，面向真实项目中的对话协作、任务执行、命令验证与工程管理。

EOS App 是官方桌面应用发行仓库，提供安装包、版本说明、截图与基础使用介绍。

本仓库不提供 EOS App 桌面端源码。EOS App 的核心能力基于开源项目 [EOS CLI](https://github.com/eosaios/eos) 打造。

当前 `v1.0.0-beta.4`，随包分发签名 Rust Core（sha256 校验 + Ed25519 验签），对外发布覆盖三端：Windows（setup 安装器 + 便携 zip）、macOS（dmg 安装镜像 + 便携 tar.gz，Intel + Apple Silicon）、Linux（amd64 + arm64）。

- 发行仓库：https://github.com/eosaios/eos-app
- 问题反馈：https://github.com/eosaios/eos-app/issues
- 版本下载：https://github.com/eosaios/eos-app/releases

## 为什么选择 EOS App？

| 诉求 | EOS App |
|---|---|
| 希望用桌面界面承接 AI 编码流程 | 统一收口对话、任务、命令与工程入口 |
| 不想在多个工具之间来回切换 | 会话、任务、Bash、Worktree、诊断集中管理 |
| 需要更稳定地查看上下文和状态 | 提供模型、规则、上下文、成本、诊断等独立页面 |
| 需要更适合长期使用的工作台 | 命令面板、通知、连接管理与系统设置集中可见 |

## 核心能力

- 对话工作区：围绕项目发起新对话，集中承接消息、附件与上下文协作
- 任务中心：查看后台任务状态、执行进度与可中止作业
- Bash 工作面：补充验证命令、查看最近输出与失败信息
- Worktree 入口：辅助处理工作树边界与分支作业位
- 连接与模型：统一管理模型连接、可用状态与相关配置
- 规则与上下文：集中维护模型指令、上下文摘要与成本观察
- 工程辅助页：提供 LSP、Diagnostics、Settings、Notifications 等页面

## 适用场景

- 希望在桌面端集中处理 AI 编码与工程协作的个人开发者
- 需要一体化查看会话、任务、命令结果与系统状态的重度用户
- 更偏好图形界面而非纯终端交互的 EOS 用户

## 下载与安装包

本仓库面向桌面应用分发，公开内容以 README、版本说明和安装包为主。

每个 Release 提供的发布资产：

- Windows x64 setup 安装器（`eos-app-setup-<版本>.exe`）与便携压缩包
- macOS dmg 安装镜像（Intel 与 Apple Silicon，拖拽安装）与便携 tar.gz
- Linux tar.gz（amd64 与 arm64）
- 校验文件 `SHA256SUMS.txt`

具体资产名称、版本号与校验信息以每个 Release 页面为准。

## 界面预览

主工作台总览（macOS，窗口控制为原生交通灯风格；Windows / Linux 为对应的平台风格按钮）：

![EOS App 主工作台总览](https://github.com/eosaios/eos-app/releases/download/v1.0.0-beta.4/workspace-overview.png)

- 左侧提供新对话、技能和应用、自动化与会话入口
- 中央区域用于承接对话内容、快捷建议与主要工作流
- 底部输入区支持直接发起新任务，Bash 终端随附在工作台下方

## 许可证

本仓库采用 EOS App 安装包与文档非商用许可证 v1.0，详见 [LICENSE](./LICENSE)：

- 个人/非商业用途可免费下载安装和使用官方安装包
- 允许在非商业场景下原样分发官方安装包与随附文档
- 本仓库不提供 EOS App 桌面端源码
- 禁止任何商业使用（含企业内部生产用途、收费服务、SaaS、二次商业分发）
- 商业使用必须获得版权人单独书面授权

## 联系方式

- 问题反馈：https://github.com/eosaios/eos-app/issues
- 商业合作/授权咨询：legal@eosaios.com

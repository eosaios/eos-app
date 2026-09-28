# EOS App 发行说明（DISTRIBUTION）

> 记录桌面端的对外发行配置，供接手者（含 AI 会话）直接引用。最后更新：2026-09-28。
> 账号与凭证统一记录在私有仓 `eos-app-src` 的 `RELEASE_CREDENTIALS.md`，本文件不重复。
> 构建流程细节见私有仓 `eos-app-src` 的 `RELEASING.md`。

## winget 包

- 包 ID：**`EOSAIOS.EOSApp`**（Inno Setup 安装器，`UpgradeBehavior: install`）
- 首次提交：microsoft/winget-pkgs PR #442426（2026-09-28 已过自动校验）
- beta 策略：单包 ID 走到底，版本号如实写 `1.0.0-beta.N`；发正式版后 beta 用户无缝升级
- 安装命令：`winget install EOSAIOS.EOSApp`
- **WebView2 依赖待办**：winget-pkgs 不允许新版包声明 Dependencies，待包发布后需单独提 PR 追加 `Microsoft.Edge.WebView2Runtime` 依赖（安装器自身不装 WebView2；Win11 / 带 Edge 的 Win10 均自带）

## 发版自动化

`.github/workflows/release.yml` 末尾的 `winget` job：Release 创建后自动跑 wingetcreate `update --submit` 提 manifest PR。

- 前置：本仓库 Settings → Secrets 已配 `WINGET_TOKEN`（见私有仓凭证文档）
- 开关：仓库 Variables 设 `WINGET_SUBMIT=off` 停用
- 首次手动 PR 合并前自动 job 失败属预期

## 代码签名现状（未购买任何证书）

| 端 | 现状 | 后续方案 |
| --- | --- | --- |
| Windows | 未签名，双击 setup 弹 SmartScreen 蓝屏 | 已用 winget 渠道规避（winget 安装不弹）；要根治选 Azure Trusted Signing（约 $10/月）或开源项目免费 SignPath |
| macOS | ad-hoc 签名、未公证，Gatekeeper 拦截 | README 写明"右键 → 打开"绕过；唯一干净解是 Apple Developer $99/年，按需再交 |
| Linux | 无门槛 | 无需处理 |

## 文案红线

安装包许可证为非商用（个人/非商用免费，商用需书面授权 legal@eosaios.com），**对外文案禁止"开源 / open-source"字样**。核心能力基于 EOS CLI 的 Rust 内核（注意：也不称 EOS CLI 为"开源项目"）。

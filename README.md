# Digital Immortality 使用说明

本文档面向第一次接入 `digital-immortality` 的用户，按实际使用顺序介绍完整流程。

## 0. 环境准备

在开始前，请先满足以下任一条件：

- 已安装 `uv`（推荐）
- 已安装 `Python 3.13+` 环境

安装 `uv`，请在 terminal 执行：

mac / linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 1. 安装 CLI

已安装 uv:

```bash
uv tool install digital-immortality --default-index https://pypi.org/simple
```

未安装 uv:

```bash
pip install digital-immortality --default-index https://pypi.org/simple
```

安装完成后，重启 terminal，确认命令可用：

```bash
immortality --help
```

## 2. 首次执行健康检查（预期失败）

执行：

```bash
immortality doctor
```

首次检查通常不会通过，这是正常现象。`doctor` 会明确提示缺失项，主要覆盖以下检查：

- `.env` 环境变量是否已配置
- 数据库是否可连接
- Python 版本是否满足要求（`>=3.13`）
- 依赖是否安装完整

## 3. 执行 setup 配置环境变量

执行：

```bash
immortality setup
```

该命令会引导你填写必要配置，并在本地创建目录：

- `~/.immortality/.env`：环境变量配置文件
- `~/.immortality/logs/`：后续服务运行日志目录

## 4. 再次执行 doctor（预期通过）

配置完成后再次检查：

```bash
immortality doctor
```

理论上此时应通过所有检查项；若未通过，请按输出中的 `guidance` 逐项修复。

## 5. 启动飞书服务

最终启动命令：

```bash
immortality lark-service start
```

说明：

- `lark-service start` 会先自动执行一次 `doctor`
- 如果检查失败，服务不会启动，并直接输出修复提示
- 启动成功后，日志会持续写入 `~/.immortality/logs/`

# Contributing Guide

本文档说明本项目的日常开发与发布流程。

## 开发与合并流程

1. 从 `develop` 或其他功能分支进行开发。
2. 完成开发后将代码 push 到 GitHub 对应分支。
3. 在 GitHub 发起 PR，并合并到 `main`。

## 发布流程（PyPI）

本项目的 PyPI 发布由 GitHub Actions 自动完成，触发条件为 push `v*` tag（见 `.github/workflows/publish.yml`）。

标准发布步骤如下：

1. 本地切换到 `main` 分支。
2. 拉取远端最新代码。
3. 创建版本标签，例如 `v1.2.3`。
4. 推送该 tag 到远端，自动触发 PyPI 发布流水线。

## 一键执行发布步骤（3-5）

已提供脚本：`scripts/publish.sh`，用于执行以下操作：

1. 切换到 `main`
2. `git pull --ff-only origin main`
3. 自动将 `pyproject.toml` 的 `version` 更新为目标版本并提交
4. `uv build` + `uvx twine check dist/*` 校验包
5. 创建 `vX.Y.Z` tag
6. 推送 `main` 和 tag 到 `origin`

使用示例：

```bash
./scripts/publish.sh 1.2.3
```

或：

```bash
./scripts/publish.sh v1.2.3
```

## 注意事项

- 请确保你对远端仓库有 push tag 权限。
- tag 一旦推送会触发发布，请先确认版本号与变更内容正确。
- 若本地有未提交修改，建议先提交或暂存后再执行发布脚本。

# Digital Immortality 使用说明

> 建议优先在服务器 / 开发机 `Devbox` / 沙箱 `Sandbox` 环境使用并持续运行，避免本地电脑关机、重启或休眠后需要重复启动服务，影响稳定性与可用性。

## 环境准备

在开始前，请先满足以下任一条件：

- 已安装 `uv`（推荐）
- 已安装 `Python 3.12+` 环境

安装 `uv`，请在 `terminal` 执行：

`mac / linux`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`windows`：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

如果你计划使用 `Docker` 自动配置 `PostgreSQL` 数据库（推荐；若不使用 `Docker`，需要手动配置数据库，较繁琐），请提前配置 `Docker` 环境：

`mac / windows`：

- 安装 `Docker Desktop`：[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
- 安装后启动 `Docker Desktop`，等待 `Docker Engine` 就绪

`linux`：

- 安装 `Docker Engine`：[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)
- 安装 `Docker Compose` 插件：[https://docs.docker.com/compose/install/linux/](https://docs.docker.com/compose/install/linux/)

安装完成后，请在 `terminal` 验证：

```bash
docker --version
docker compose version
# 或
docker-compose --version
```

## 安装 CLI

已安装 `uv`：

```bash
uv tool install digital-immortality --default-index https://pypi.org/simple
```

未安装 `uv`：

```bash
pip install digital-immortality -i https://pypi.org/simple
```

安装完成后，重启 `terminal`，确认命令可用：

```bash
immortality --help
```

## 首次执行健康检查（预期失败）

执行：

```bash
immortality doctor
```

首次检查通常不会通过，这是正常现象。`doctor` 会明确提示缺失项，主要覆盖以下检查：

- `.env` 环境变量是否已配置
- 数据库是否可连接
- `Python` 版本是否满足要求（`>= 3.12`）
- 依赖是否安装完整

## PostgreSQL 手动配置（不推荐）

不推荐手动配置 `PostgreSQL`，建议优先使用 `Docker setup (recommended)`，可避免在本地配置数据库的复杂性。

如果你必须使用手动模式，请确保 `PostgreSQL` 满足以下要求：

- `PostgreSQL` 版本：`>= 16`
- 支持 `pgvector` 扩展
- 数据库可被本机访问，且账号具备建库与建扩展权限

可参考以下安装流程：

`mac`（`Homebrew`）：

```bash
brew install postgresql@16 pgvector
brew services start postgresql@16
```

`linux`（`Debian/Ubuntu` 示例）：

```bash
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16 postgresql-16-pgvector
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

如果是远程连接场景，还需额外配置：

- 在 `postgresql.conf` 中设置 `listen_addresses = '*'`（或指定允许访问的网卡地址）
- 在 `pg_hba.conf` 中增加允许应用服务器 IP 的访问规则
- 放通 `5432` 端口（建议仅对内网开放）

连接信息示例（后续在 `immortality setup -> Manual setup` 中填写）：

- `db_user=<your_db_user>`
- `db_password=<your_db_password>`
- `db_host=127.0.0.1`
- `db_port=5432`

## 方舟模型配置

> 当前服务仅支持 [火山方舟平台 (https://console.volcengine.com/ark)](https://console.volcengine.com/ark) 配置的模型，但你可以在火山方舟平台选择其支持的其他模型。

- 注册并登录平台
- 创建 `API Key` 并保存，后续在 `setup` 过程中作为 `ark_api_key` 填写

![创建 API Key](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_fabf2e7eff.png)

### 简要配置

> 风险：可能遇到超过模型 `TPM`（`Token Per Minute`）的情况，体验会略有波动。

后续 `setup` 过程中：

- `lite_model_endpoint_or_model_id` 填写：`doubao-seed-2-0-lite-260215`
- `mini_model_endpoint_or_model_id` 填写：`doubao-seed-2-0-mini-260215`
- `embedding_model_endpoint_or_model_id` 填写：`doubao-embedding-vision-251215`

### 高稳定性配置

为三类模型分别创建推理接入点。

![step 1](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_340033c7c2.png)
![step 2](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_7715f5a3d1.png)

选择适合的模型。推荐创建 `3` 个接入点，分别包含：`Lite` 模型、`Mini` 模型和 `Embedding` 模型。

![step 3](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_d4976c0f00.png)

分别复制三类模型的 `endpoint_id`，在 `setup` 时填写到以下字段：

- `lite_model_endpoint_or_model_id`
- `mini_model_endpoint_or_model_id`
- `embedding_model_endpoint_or_model_id`

![step 4](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_221bd3e028.png)

### 提示（不建议）

也可只配置 `Lite Model` 和 `Embedding Model`，不配置 `Mini Model`。这种情况下，需要在 `setup` 时将 `mini_model_endpoint_or_model_id` 填写为 `lite_model_endpoint_or_model_id` 的值（即 `Lite Model` 的 `endpoint_id`）。

## 飞书机器人配置

1. 登录 [飞书开放平台](https://open.larkoffice.com/app)。
   建议使用个人账号，否则**可能**需要企业审核。
2. 创建企业自建应用，并添加应用能力 **机器人**。

![创建应用](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_24eca5a3c7.png)

3. 进入 **权限管理**，选择 **批量导入权限**，并导入以下权限配置。

![批量导入权限](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_f4ea138847.png)

```json
{
    "scopes": {
        "tenant": [
            "application:application.app_message_stats.overview:readonly",
            "application:application:self_manage",
            "application:bot.menu:write",
            "base:app:copy",
            "base:app:create",
            "base:app:read",
            "base:app:update",
            "base:collaborator:create",
            "base:collaborator:delete",
            "base:collaborator:read",
            "base:dashboard:copy",
            "base:dashboard:read",
            "base:field:create",
            "base:field:delete",
            "base:field:read",
            "base:field:update",
            "base:form:read",
            "base:form:update",
            "base:record:create",
            "base:record:delete",
            "base:record:read",
            "base:record:retrieve",
            "base:record:update",
            "base:role:create",
            "base:role:delete",
            "base:role:read",
            "base:role:update",
            "base:table:create",
            "base:table:delete",
            "base:table:read",
            "base:table:update",
            "base:view:read",
            "base:view:write_only",
            "cardkit:card:write",
            "contact:contact.base:readonly",
            "contact:user.employee_id:readonly",
            "docs:document.content:read",
            "docx:document.block:convert",
            "docx:document:create",
            "docx:document:readonly",
            "docx:document:write_only",
            "drive:drive.metadata:readonly",
            "drive:drive.search:readonly",
            "drive:drive:version",
            "drive:drive:version:readonly",
            "event:ip_list",
            "im:chat.access_event.bot_p2p_chat:read",
            "im:chat.members:bot_access",
            "im:chat:read",
            "im:chat:update",
            "im:message.group_at_msg:readonly",
            "im:message.p2p_msg:readonly",
            "im:message.pins:read",
            "im:message.pins:write_only",
            "im:message.reactions:read",
            "im:message.reactions:write_only",
            "im:message:readonly",
            "im:message:recall",
            "im:message:send_as_bot",
            "im:message:send_multi_users",
            "im:message:send_sys_msg",
            "im:message:update",
            "im:resource",
            "wiki:wiki:readonly"
        ],
        "user": [
            "base:table:create",
            "contact:contact.base:readonly",
            "contact:user.employee_id:readonly",
            "docx:document.block:convert",
            "im:chat.access_event.bot_p2p_chat:read"
        ]
    }
}
```

4. 进入 **事件与回调**：
    - 订阅方式选择 **使用长连接接收事件**
    - 添加事件 **接收消息**

![事件与回调](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_b6fd35b4e1.png)

5. （可选，建议）进入 **机器人**，编辑 **机器人自定义菜单**：
    - 状态选择 **开启**
    - 添加 `3` 个菜单：
        - `/menu`
        - `/list_available_persons`
        - `/clear_current_person`

![菜单配置](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_80b5da72c0.png)

6. 进入 **版本管理与发布**，创建版本并发布。

> 通常情况是免审发布。若需要企业审核，请使用个人账号配置飞书机器人。
>
> ![机器人发布](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_22762312f7.png)

7. 进入 **凭证与基础信息**，保存 **App ID** 和 **App Secret**。
   在 `setup` 时填写到以下字段：
    - `lark_bot_app_id`
    - `lark_bot_app_secret`

![凭证与基础信息](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_a16255e0ac.png)

## 飞书卡片配置

1. 进入 [飞书卡片搭建工具](https://open.feishu.cn/cardkit)。
2. 创建空白卡片。

![创建空白卡片](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_c2c2a3080e.png)

3. 导入卡片：
    - 下载 [Immortality.card](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/Immortality.card)（项目根目录也提供 `Immortality.card`）
    - 在卡片搭建工具中完成导入

![导入卡片](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_e6c33f6e20.png)

4. 添加自定义机器人 / 应用，并设置为 **所有应用**。

![添加自定义机器人 / 应用](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_7156e01eee.png)

5. 保存并发布。
6. 记录左上角 `Template ID`，并在 `setup` 时填写到 `lark_card_template_id`。

![Template ID](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_8bfd84df6a.png)

## 执行 setup 配置环境变量

执行：

```bash
immortality setup
```

该命令会先让你选择数据库配置方式：

- `Docker setup (recommended)`：推荐。自动拉起 `PostgreSQL` 并填充本地数据库连接参数
- `Manual setup`：手动填写数据库连接参数（保持旧行为）

当你选择 `Docker setup (recommended)` 时，`CLI` 会自动完成：

- 检查 `docker` / `docker compose`（兼容 `docker-compose`）
- 在 `~/.immortality/` 写入并使用 `docker` 资源文件
- 启动 `PostgreSQL`（镜像为 `pgvector/pgvector:pg16`）
- 确保存在两个数据库：
    - `immortality`
    - `immortality_checkpoints`
- 初始化 `vector` 扩展（`CREATE EXTENSION IF NOT EXISTS vector;`）

然后继续引导你填写其余必要配置，并在本地创建目录：

- `~/.immortality/.env`：环境变量配置文件
- `~/.immortality/logs/`：后续服务运行日志目录
- `~/.immortality/docker-compose.yml`：`Docker` 模式数据库编排文件

## 再次执行 doctor（预期通过）

配置完成后再次检查：

```bash
immortality doctor
```

理论上此时应通过所有检查项；若未通过，请按输出中的 `guidance` 逐项修复。

## CLI 注册或登录

若没有 digital-immortality 账号，需先注册，再进行登录。

```bash
immortality auth register
```

若已有 digital-immortality 账号，直接登录即可。

```bash
immortality auth login
```

## 绑定飞书 open_id

### 获取飞书 open_id

访问并登录 [https://open.larkoffice.com/document/server-docs/im-v1/message/create](https://open.larkoffice.com/document/server-docs/im-v1/message/create)。在右侧 **API 调试台** 的 **查询参数** 中，选择 `open_id`。之后点击下方 **快速复制 open_id**

![获取飞书 open_id](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_c03f823bce.png)

### CLI 绑定飞书 open_id

```bash
immortality auth bind-lark --lark-open-id <open_id>
```

## 启动飞书服务

前台启动（用于调试）：

```bash
immortality lark-service start
```

启动说明：

- `lark-service start` 会先自动执行一次 `doctor`
- 如果检查失败，服务不会启动，并直接输出修复提示
- 启动成功后，日志会持续写入 `~/.immortality/logs/`

### 推荐：后台启动（生产 / 长时运行）

实际使用建议采用后台方式启动，避免阻塞当前终端：

```bash
nohup immortality lark-service start &
```

该命令会通过 `nohup` 在后台运行服务。

查看服务 `PID`：

```bash
pgrep -af immortality
```

终止服务：

```bash
kill <pid>
```

## 查看日志

```bash
immortality logs [--date YYYYMMDD]
```

其中，`--date` 为可选参数，默认读取当天日志。

## 同步细粒度人物形象信息到人物固有画像

> 该任务耗时较长，建议配置为 `Cronjob` 定时任务，每天或每两天执行一次。

完善人物形象后，可在 `CLI` 执行同步：

```bash
immortality fr sync-feeds [--id <fr_id>]
```

参数说明：

- `--id`：可选参数；不填写时，默认同步当前用户的全部 `FR`。

## Docker 常见问题

### collation version mismatch

若你在 `immortality setup`（`Docker` 模式）看到类似错误：

- `database "..." has a collation version mismatch`
- `template database "template1" has a collation version mismatch`

通常是因为你复用了旧的 `PostgreSQL volume`（历史镜像与当前镜像底层库版本不一致）。

本地开发建议直接重建 `volume`（会清空本地数据库数据）：

```bash
docker compose -f ~/.immortality/docker-compose.yml down -v
docker compose -f ~/.immortality/docker-compose.yml up -d postgres
```

然后重新执行：

```bash
immortality setup
immortality doctor
```

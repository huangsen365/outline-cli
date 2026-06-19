[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

# Outline VPN 命令行工具

一个简单的命令行工具，用于通过 Outline Server API 管理 Outline VPN 访问密钥。

## 安装

```bash
# 克隆仓库
git clone https://github.com/huangsen365/outline-cli.git
cd outline-cli

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install outline-vpn-api python-dotenv
```

## 配置

首次运行时，CLI 会提示您输入 Outline 服务器凭据：

- **API URL**：可在 Outline Manager 中找到（例如：`https://x.x.x.x:port/prefix`）
- **Certificate SHA256**：Outline Manager 中的证书指纹

凭据将保存到 `.env` 文件中供后续使用。

## 使用方法

```bash
# 列出所有访问密钥
python outline_cli.py list

# 显示指定密钥的完整详情
python outline_cli.py show <key_id>

# 创建新的访问密钥
python outline_cli.py add
python outline_cli.py add --name "我的设备"

# 删除访问密钥
python outline_cli.py delete <key_id>

# 重命名访问密钥
python outline_cli.py rename <key_id> "新名称"

# 设置流量限制（单位：MB，设为 0 则移除限制）
python outline_cli.py limit <key_id> 1024
python outline_cli.py limit <key_id> 0
```

## 示例输出

```
$ python outline_cli.py list
ID     Name                 Usage (MB)   Access URL
--------------------------------------------------------------------------------
1      设备-A               125.3        ss://Y2hhY...@1.2.3.4:12345/?outline=1
2      设备-B               0.0          ss://Y2hhY...@1.2.3.4:12345/?outline=1
```

## Clash 配置模板

项目中包含一个可直接填写的 Clash 代理配置模板
[`clash-template.yaml`](clash-template.yaml)。复制该文件，将其中的 `<...>`
占位符替换为您访问密钥中的值，然后在 Clash 客户端中加载即可。

获取某个密钥的 `ss://` 访问 URL：

```bash
python outline_cli.py --profile <profile> show <key_id>
```

该 URL 的格式为 `ss://<base64>@<server>:<port>/?outline=1`。解码其中的
`<base64>` 部分即可得到 `<cipher>:<password>`：

```bash
echo '<base64>' | base64 -d
# -> chacha20-ietf-poly1305:<password>
```

填写后的示例：

```yaml
proxies:
  - name: "clash-mi-on-mba-m4-jp"
    type: ss
    server: example.wansio.com
    port: 2132
    cipher: chacha20-ietf-poly1305
    password: "your-password-here"
    udp: true

proxy-groups:
  - name: "Proxy"
    type: select
    proxies:
      - "clash-mi-on-mba-m4-jp"
      - DIRECT

rules:
  - GEOIP,LAN,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,Proxy
```

> **注意：** 填写后的配置包含您密钥的密码。请勿提交到版本控制——`.gitignore`
> 已忽略 `clash-*.yaml`（模板文件除外）。

## 许可证

MIT

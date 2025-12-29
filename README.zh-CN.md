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

## 许可证

MIT

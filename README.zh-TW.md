[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

# Outline VPN 命令列工具

一個簡單的命令列工具，用於透過 Outline Server API 管理 Outline VPN 存取金鑰。

## 安裝

```bash
# 複製儲存庫
git clone https://github.com/huangsen365/outline-cli.git
cd outline-cli

# 建立虛擬環境
python -m venv venv
source venv/bin/activate

# 安裝相依套件
pip install outline-vpn-api python-dotenv
```

## 設定

首次執行時，CLI 會提示您輸入 Outline 伺服器憑證：

- **API URL**：可在 Outline Manager 中找到（例如：`https://x.x.x.x:port/prefix`）
- **Certificate SHA256**：Outline Manager 中的憑證指紋

憑證將儲存至 `.env` 檔案供後續使用。

## 使用方法

```bash
# 列出所有存取金鑰
python outline_cli.py list

# 顯示指定金鑰的完整詳情
python outline_cli.py show <key_id>

# 建立新的存取金鑰
python outline_cli.py add
python outline_cli.py add --name "我的裝置"

# 刪除存取金鑰
python outline_cli.py delete <key_id>

# 重新命名存取金鑰
python outline_cli.py rename <key_id> "新名稱"

# 設定流量限制（單位：MB，設為 0 則移除限制）
python outline_cli.py limit <key_id> 1024
python outline_cli.py limit <key_id> 0
```

## 範例輸出

```
$ python outline_cli.py list
ID     Name                 Usage (MB)   Access URL
--------------------------------------------------------------------------------
1      裝置-A               125.3        ss://Y2hhY...@1.2.3.4:12345/?outline=1
2      裝置-B               0.0          ss://Y2hhY...@1.2.3.4:12345/?outline=1
```

## 授權條款

MIT

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

# 可選：僅在使用存取金鑰測試工具（ss_test.py / ss_proxy.py）時需要
pip install cryptography
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

## 測試存取金鑰

兩個輔助腳本可用於驗證某個 `ss://` 金鑰是否正常運作。它們都以存取 URL 作為參數，
支援 Outline 使用的 `chacha20-ietf-poly1305` 加密方式，並依賴 `cryptography`
套件（`pip install cryptography`）。

```bash
# 一次性連線檢查：透過該金鑰通道發送一個 HTTP 請求，
# 並印出每個協定步驟（交握、加密、回應）。
python ss_test.py 'ss://<base64>@host:port/?outline=1'

# 將該金鑰公開為本機 SOCKS5 代理，讓任何用戶端都可透過它路由流量。
python ss_proxy.py 'ss://<base64>@host:port/?outline=1' --listen 127.0.0.1:1080
curl --socks5-hostname 127.0.0.1:1080 https://api.ipify.org
```

## Clash 設定範本

專案中包含一個可直接填寫的 Clash 代理設定範本
[`clash-template.yaml`](clash-template.yaml)。複製該檔案，將其中的 `<...>`
佔位符替換為您存取金鑰中的值，然後在 Clash 用戶端中載入即可。

取得某個金鑰的 `ss://` 存取 URL：

```bash
python outline_cli.py --profile <profile> show <key_id>
```

該 URL 的格式為 `ss://<base64>@<server>:<port>/?outline=1`。解碼其中的
`<base64>` 部分即可得到 `<cipher>:<password>`：

```bash
echo '<base64>' | base64 -d
# -> chacha20-ietf-poly1305:<password>
```

填寫後的範例：

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

> **注意：** 填寫後的設定包含您金鑰的密碼。請勿提交至版本控制——`.gitignore`
> 已忽略 `clash-*.yaml`（範本檔案除外）。

## 授權條款

MIT

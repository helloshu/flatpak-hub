# Flatpak Hub (`helloshu/flatpak-hub`)

基于 Flatpak `extra-data` 架构构建的轻量级公开 OSTree 软件源，托管于 GitHub Pages（无 `gh-pages` 分支历史膨胀，构建耗时约 20 秒）。

软件源仅分发数 KB 的桌面元数据、沙盒权限与离线解包脚本（`apply_extra`）；实际安装包在客户端执行 `flatpak install` / `flatpak update` 时直接从公开 GitHub Releases 下载并做严格 `SHA-256` 与字节大小校验。

## 1. 客户端接入与日常更新

```bash
# 首次添加软件源（已内置 GPG 公钥自动信任）
flatpak --user remote-add --if-not-exists flatpak-hub https://helloshu.github.io/flatpak-hub/flatpak-hub.flatpakrepo

# 安装应用
flatpak --user install flatpak-hub com.rssh.app

# 后续自动升级所有已安装应用
flatpak --user update
```

## 2. 已收录应用

| App ID | 应用名称 | 运行时底座 | 上游发版源 |
| :--- | :--- | :--- | :--- |
| `com.rssh.app` | [RSSH](https://github.com/shihuili1218/rssh) | `org.gnome.Platform//51` | [`helloshu/auto-builds`](https://github.com/helloshu/auto-builds) (`rssh-*`) |
| `io.github.anywhere_labs.DshNext` | [DSH NEXT](https://github.com/anywhere-labs/dsh-desktop)（社区版，x86_64） | `org.freedesktop.Platform//25.08` + `org.electronjs.Electron2.BaseApp` | [`helloshu/auto-builds`](https://github.com/helloshu/auto-builds) (`dsh-desktop-v*`) |

## 3. 自动推送接口（供构建仓库发版末尾调用）

构建仓库发布新 Release 后，向本仓发送 `repository_dispatch`（`event_type: upstream-release`）即可在数十秒内自动完成 Pin 更新、GPG 重签与 Pages 发布：

```bash
curl -fsSL -X POST \
  -H "Authorization: Bearer ${FLATPAK_HUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/helloshu/flatpak-hub/dispatches \
  -d '{
    "event_type": "upstream-release",
    "client_payload": {
      "app_id": "com.rssh.app",
      "version": "1.0.8",
      "url": "https://github.com/helloshu/auto-builds/releases/download/rssh-v1.0.8/rssh-1.0.8-linux-x86_64.deb",
      "sha256": "<64-hex-sha256>",
      "size": 21476446
    }
  }'
```

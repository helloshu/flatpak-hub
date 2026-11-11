# flatpak-hub — Agent Guidelines

`helloshu/flatpak-hub` 是基于 Flatpak `extra-data` 机制与 GitHub Pages 构建的轻量级公开 OSTree 软件源。

## 1. 目录与核心脚本职责

- `config/repo.json`：软件源全局配置（名称、主页、GPG 指纹等）。
- `registry/<AppID>/`：每个已收录应用的元数据目录，包含：
  - `manifest.json`：Flatpak 构建清单（使用 `extra-data` 指向公开 GitHub Releases 安装包 URL、`sha256` 与字节 `size`）。
  - `pin.json`：当前固定版本号与上游资产校验信息。
  - `apply_extra`：客户端安装时在沙盒内执行的离线解包脚本。
  - `<AppID>.metainfo.xml` / `<AppID>.desktop` / 图标资源。
- `scripts/update_pin.py`：校验并更新 `registry/<AppID>/pin.json` 与 `manifest.json` 中的版本、`url`、`sha256`、`size`。
- `scripts/build_ostree.sh`：编译各应用元数据到单一 OSTree 仓库并使用 GPG 私钥签名生成静态站点产物。
- `scripts/render_site.py`：生成 `.flatpakrepo` 描述文件与静态索引页。

## 2. 新增或更新应用规范

- 所有 `extra-data` 下载链接必须使用公开 HTTPS 直链，且同时严格匹配 `sha256`（64 位小写十六进制）与精确字节大小 `size`。
- `apply_extra` 运行在无网络的客户端安装沙盒中，不得在 `apply_extra` 内发起任何网络请求。
- 新增应用后请同步更新 [`README.md`](README.md) 中的已收录应用表格，并在上游构建仓库发版末尾配置 `event_type: upstream-release` 的 `repository_dispatch` 通知。

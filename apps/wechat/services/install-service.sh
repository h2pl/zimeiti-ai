#!/usr/bin/env bash
# 安装 zimeiti 微信桥为开机自驻服务（systemd --user / launchd）。
#
#   bash services/install-service.sh              # 安装并启动
#   bash services/install-service.sh --uninstall  # 卸载
#
# Windows 无对应服务形态——请用「任务计划程序」或「启动文件夹」（见 README）。

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WECHAT_DIR="$(cd "$HERE/.." && pwd)"
ZIMEITI_API="${ZIMEITI_API:-http://127.0.0.1:8000}"
UNIT_NAME="zimeiti-wechat"
PLIST_LABEL="com.zimeiti.wechat"
UNINSTALL=0
[[ "${1:-}" == "--uninstall" ]] && UNINSTALL=1

detect_platform() {
  case "$(uname -s)" in
    Linux) echo "systemd" ;;
    Darwin) echo "launchd" ;;
    *) echo "unsupported" ;;
  esac
}

render() {
  # $1=模板 $2=输出：替换占位符
  local node_bin
  node_bin="$(command -v node || true)"
  [[ -z "$node_bin" ]] && { echo "找不到 node——请先安装 Node ≥18"; exit 1; }
  sed -e "s|__WECHAT_DIR__|$WECHAT_DIR|g" \
      -e "s|__ZIMEITI_API__|$ZIMEITI_API|g" \
      -e "s|__NODE_BIN__|$node_bin|g" \
      "$1" > "$2"
}

case "$(detect_platform)" in
  systemd)
    UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    if [[ $UNINSTALL -eq 1 ]]; then
      systemctl --user disable --now "$UNIT_NAME" 2>/dev/null || true
      rm -f "$UNIT_DIR/$UNIT_NAME.service"
      systemctl --user daemon-reload
      echo "已卸载 systemd 用户服务"
      exit 0
    fi
    mkdir -p "$UNIT_DIR"
    render "$HERE/$UNIT_NAME.service" "$UNIT_DIR/$UNIT_NAME.service"
    systemctl --user daemon-reload
    systemctl --user enable --now "$UNIT_NAME"
    echo "已安装并启动：systemctl --user status $UNIT_NAME"
    echo "日志：journalctl --user -u $UNIT_NAME -f"
    ;;
  launchd)
    AGENTS_DIR="$HOME/Library/LaunchAgents"
    if [[ $UNINSTALL -eq 1 ]]; then
      launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || true
      rm -f "$AGENTS_DIR/$PLIST_LABEL.plist"
      echo "已卸载 launchd agent"
      exit 0
    fi
    mkdir -p "$AGENTS_DIR"
    render "$HERE/$PLIST_LABEL.plist" "$AGENTS_DIR/$PLIST_LABEL.plist"
    launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$AGENTS_DIR/$PLIST_LABEL.plist"
    launchctl enable "gui/$(id -u)/$PLIST_LABEL"
    echo "已安装并加载：launchctl list | grep $PLIST_LABEL"
    echo "日志：$WECHAT_DIR/state/bridge.log"
    ;;
  *)
    echo "当前平台（$(uname -s)）不支持自动服务安装。"
    echo "Windows 请使用「任务计划程序」或「启动文件夹」，步骤见 apps/wechat/README.md。"
    exit 1
    ;;
esac

#!/bin/bash
# 热梗工作台 - 同步脚本
# 将最新页面和数据同步到 deploy 目录，供手动 CloudStudio 部署使用
# GitHub Pages 自动部署由 .github/workflows/daily-update.yml 处理
#
# 用法: ./deploy.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$DIR/deploy"

echo "==> 同步文件到部署目录 (CloudStudio legacy)..."
mkdir -p "$DEPLOY_DIR/data"
cp "$DIR/index.html" "$DEPLOY_DIR/index.html"
cp "$DIR/data/data.js" "$DEPLOY_DIR/data/data.js"
echo "    index.html -> deploy/"
echo "    data/data.js -> deploy/data/"

echo ""
echo "==> 提示: GitHub Pages 自动部署无需此脚本。"
echo "    此目录仅供 CloudStudio 手动部署备用。"

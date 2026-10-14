#!/bin/bash
# 创建 GitHub 仓库并推送本项目（一步到位）。
#
# 用法:
#   sh push-to-github.sh <GITHUB_TOKEN> [仓库名]
#
# 例:
#   sh push-to-github.sh ghp_xxxxxxxxxxxx
#   sh push-to-github.sh ghp_xxxxxxxxxxxx my-repo-name
#
# 需要的 token 权限：
#   - classic token：勾 repo（私有仓库再加 workflow）
#   - fine-grained token：Repository permissions → Contents: Read and write、
#     Administration: Read and write（建仓库需要），并允许访问你的账号
#
# token 只用于这一次 curl 和这一条 git push，不会写进 .git/config。
set -e

TOKEN="$1"
REPO="${2:-quark-clouddrive-entry-extension}"
OWNER="${GH_OWNER:-yncg}"
DESC="夸克网盘入口扩展：点一下云朵图标直接打开夸克网盘首页（可自定义链接）"

if [ -z "$TOKEN" ]; then
  echo "用法: sh push-to-github.sh <GITHUB_TOKEN> [仓库名]"
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# 确保是 git 仓库且有提交
if [ ! -d .git ]; then
  echo "[1/4] 初始化 git 仓库"
  git init -q
  git config user.name "${GH_NAME:-$OWNER}"
  git config user.email "${GH_EMAIL:-$OWNER@users.noreply.github.com}"
  git add -A
  git commit -q -m "feat: 夸克网盘入口扩展（点一下直接打开网盘首页）"
else
  echo "[1/4] 已存在 git 仓库，跳过初始化"
fi

echo "[2/4] 创建远端仓库 $OWNER/$REPO（已存在则跳过）"
CODE=$(curl -s -o /tmp/gh_create_repo.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO\",\"description\":\"$DESC\",\"private\":false,\"has_issues\":true,\"has_wiki\":false}")
case "$CODE" in
  201) echo "    已创建" ;;
  422) echo "    仓库已存在，直接推送" ;;
  401) echo "    token 无效或无权限（HTTP 401）"; sed -E 's/"token":"[^"]*"/"token":"***"/' /tmp/gh_create_repo.json | head -5; exit 1 ;;
  *)   echo "    创建失败 HTTP $CODE"; head -20 /tmp/gh_create_repo.json; exit 1 ;;
esac

echo "[3/4] 推送 main"
git push "https://$OWNER:$TOKEN@github.com/$OWNER/$REPO.git" main:main

echo "[4/4] 把远端改回干净地址（不带 token）"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$OWNER/$REPO.git"
git branch --set-upstream-to=origin/main main 2>/dev/null || true

echo
echo "完成：https://github.com/$OWNER/$REPO"

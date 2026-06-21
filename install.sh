#!/usr/bin/env bash
# yt_summary_agent 1회 셋업 (idempotent — 여러 번 실행해도 안전)
#   - yt-dlp 설치 확인/설치
#   - yt-script 를 ~/bin 에 심링크 + 실행권한
#   - ~/bin 을 PATH 에 등록(없을 때만)
#   - /yt 슬래시 커맨드를 ~/.claude/commands 에 심링크
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

echo "[1/4] yt-dlp 확인..."
if ! command -v yt-dlp >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "  yt-dlp 가 없어 brew 로 설치합니다..."
    brew install yt-dlp
  else
    echo "  brew 가 없습니다. 'pip3 install --user yt-dlp' 로 설치 후 다시 실행하세요." >&2
    exit 1
  fi
else
  echo "  OK ($(yt-dlp --version))"
fi

echo "[2/4] yt-script · ytclean.py → ~/bin 심링크..."
mkdir -p "$HOME/bin"
chmod +x "$HERE/yt-script" "$HERE/ytclean.py"
ln -sf "$HERE/yt-script" "$HOME/bin/yt-script"
ln -sf "$HERE/ytclean.py" "$HOME/bin/ytclean.py"
echo "  ~/bin/yt-script  -> $HERE/yt-script"
echo "  ~/bin/ytclean.py -> $HERE/ytclean.py"

echo "[3/4] PATH 등록..."
if ! grep -q 'HOME/bin' "$HOME/.zshrc" 2>/dev/null; then
  echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.zshrc"
  echo "  ~/.zshrc 에 ~/bin PATH 추가됨 (새 터미널부터 적용 / 지금 쓰려면: source ~/.zshrc)"
else
  echo "  이미 등록됨"
fi

echo "[4/4] /yt · /yt-push 슬래시 커맨드 → ~/.claude/commands 심링크..."
mkdir -p "$HOME/.claude/commands"
ln -sf "$HERE/yt.md" "$HOME/.claude/commands/yt.md"
ln -sf "$HERE/yt-push.md" "$HOME/.claude/commands/yt-push.md"
echo "  ~/.claude/commands/yt.md      -> $HERE/yt.md"
echo "  ~/.claude/commands/yt-push.md -> $HERE/yt-push.md"

echo
echo "완료 ✅  사용법:"
echo "  터미널:      yt-script <유튜브 URL> [언어코드]"
echo "  Claude Code: /yt <유튜브 URL>   또는 자연어로 \"이 영상 정리해줘: <URL>\""
echo "  출력 위치:   \${YT_OUT_DIR:-소스 폴더 형제 'summaries/'}  (예: 04_Agents/youtube/summaries/)"
echo
echo "  발행(선택):  /yt-push  또는  yt-script --publish [요약본.md]   (git repo 로 올리기)"
echo "    └ 먼저 대상 repo 폴더를 환경변수로 지정하세요(미설정 시 발행만 비활성):"
echo "       export YT_PUBLISH_DIR=\"\$HOME/Desktop/dev-lab/study/youtube\"   # ~/.zshrc 에 추가"

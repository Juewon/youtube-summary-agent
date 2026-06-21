---
description: 저장된 유튜브 요약본(.md)을 개인 git repo에 도메인별로 발행(push)
argument-hint: [요약본_md_경로(선택, 비우면 가장 최근 1건)]
allowed-tools: Bash(yt-script:*)
---
저장된 유튜브 요약본을 개인 git repo에 올린다(발행).

## 절차
1. `yt-script --publish "$1"` 를 실행한다.
   - `$1`(경로)이 비어 있으면 가장 최근 요약본이 자동 선택된다.
   - 발행 위치는 `YT_PUBLISH_DIR/{도메인}/{파일명}.md` 이며, 없는 도메인 폴더는 자동 생성된다.
2. 출력의 `PUSHED_FILE:`(푸시 성공) 또는 `COMMITTED_FILE:`(커밋됐으나 push 실패) 경로를 사용자에게 알린다.

## 예외 처리
- `YT_PUBLISH_DIR 가 설정돼 있지 않습니다`: 발행 대상 repo 폴더를 환경변수로 지정해야 한다고 안내한다.
  예: `export YT_PUBLISH_DIR="$HOME/Desktop/dev-lab/study/youtube"` (해당 repo는 미리 git clone 되어 있어야 함).
- `push 실패`: 네트워크/인증 문제일 수 있으니 잠시 후 재시도하거나 해당 repo에서 직접 `git push` 하도록 안내한다.

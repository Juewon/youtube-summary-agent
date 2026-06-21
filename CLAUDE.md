# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

개인용 유튜브 요약 에이전트. 유튜브 자막을 추출(`yt-dlp` + `ytclean.py`)해 자막 `.txt` 로 저장하고, **Claude Code 자체가 그 파일을 읽어 주제별로 구조화한 한국어 요약**을 만든 뒤, `yt-script --save` 로 도메인 폴더에 `.md` 로 저장한다. 별도 LLM API 키는 쓰지 않는다 — 요약·도메인 판단 두뇌는 Claude Code, 파일쓰기·경로 안전은 `yt-script` 다.

이 폴더가 **소스 오브 트루스**다. 전역 위치(`~/bin/yt-script`, `~/bin/ytclean.py`, `~/.claude/commands/yt.md`)는 여기로 향하는 **심링크**다. 전역 동작을 바꾸려면 이 폴더 파일을 수정하면 되고 재설치는 불필요(심링크라 자동 반영). git 저장소가 아니다.

## Architecture

요약은 **추출(script) → 요약(Claude) → 저장(script)** 의 협업이다 — 여러 파일을 함께 봐야 이해된다:

1. `yt-script` **추출 모드** (`yt-script <URL> [lang]`): yt-dlp 로 자막+챕터JSON 을 받아 `ytclean.py` 로 정리하고, frontmatter 헤더(title/source_url/date/lang_used/has_chapters/existing_domains) + 챕터 구간별 본문을 `_transcripts/{stem}.txt` 에 쓴다. stdout 첫 줄 **`OUTPUT_FILE: <경로>` 마커**가 계약(contract)이다.
2. `yt.md` (`/yt`): yt-script 실행 → `OUTPUT_FILE:` 경로 Read → **주제별 구조화 요약**(📌한 줄 / 🗂목차 / 주제별 `##`+불릿 / ✅결론) 생성 + 도메인 결정.
3. `yt-script` **저장 모드** (`yt-script --save <transcript_path> <domain>`, 요약 .md 를 stdin): 경로 안전 검증·도메인 정규화·`mkdir -p` 후 `{도메인}/{stem}.md` 저장, `SAVED_FILE:` 출력.
4. `yt-script` **발행 모드** (`/yt-push` → `yt-script --publish <summary_md> <topic> <filename>`): 저장된 요약 .md 를 발행 루트 `YT_PUBLISH_DIR`(외부 git repo 안 폴더)의 `{topic}/{filename}` 로 복사 후 `pull --rebase`→`add`·`commit`·`push`. **핵심: 발행 위치(폴더)·이름(파일명) 둘 다 "유튜브 출처"가 아니라 "내용"으로 Claude 가 정한다** — `/yt-push` 가 요약 내용 + `--topics`(기존 폴더)·`--ls <topic>`(기존 파일)을 보고 **폴더 재사용/신설 + 깔끔한 제목 슬러그**를 판단해 넘긴다(예: Claude Code 영상 → `claude-code/claude-code-실전-치트시트.md`). **발행 파일명은 로컬 stem(`{날짜}_{제목}_{VID}`)을 버리고 새로 짓는다**(날짜·VID 없는 읽기용 슬러그). topic 은 `--save` 도메인과 같은 규칙, filename 은 공백→하이픈·허용문자만·`.md` 보장으로 정규화. `--publish` 에서 summary 생략 시 최근 .md, topic 생략 시 로컬 도메인명, filename 생략 시 원본 파일명으로 폴백(터미널 편의). 보조(부작용 없음): `--latest`(`LATEST_FILE:`), `--topics`(`PUBLISH_ROOT:`+`TOPICS:`), `--ls [topic]`(`FILES:`). 성공 `PUSHED_FILE:`, 동일내용 `변경 없음`, push 실패 시 커밋만 남기고 `COMMITTED_FILE:`+경고. 추출/요약과 독립(`YT_PUBLISH_DIR` 없으면 발행만 비활성).

`ytclean.py` (python3, **단위테스트 대상**): VTT 정리(타임코드/cue번호/태그 제거) + **챕터 버킷팅**(`[start_i, start_{i+1})`, end_time 무시, 첫 챕터 이전은 "인트로") + **롤링 중복 머지**(`merge_rolling`, 더 긴 쪽·가장 이른 시작초 유지)를 **각 버킷 안에서** 수행(경계 넘는 자막의 오귀속 방지). 챕터 JSON 파싱 실패/빈값이면 평문 폴백. `clean_cues`/`merge_rolling`/`load_chapters`/`build_body` 함수로 import 가능. 자막만 받으므로 ffmpeg 불필요.

## 디렉터리 레이아웃

소스(이 폴더)와 출력은 `youtube/` 아래 **형제**다. 출력 기본값은 소스 폴더의 형제 `summaries/`:
```
04_Agents/youtube/
├─ yt_summary_agent/   # 소스(이 repo)
└─ summaries/          # 출력(YT_OUT_DIR 로 변경 가능)
   ├─ _transcripts/{날짜}_{제목}_{VID}.txt   # 헤더+챕터 구간 자막(중간 산출물)
   └─ {도메인}/{날짜}_{제목}_{VID}.md         # 주제별 구조화 요약(최종)
```
- 기본 출력 경로는 `yt-script` 가 자기 실제 경로(realpath)의 부모/`summaries` 로 계산 → repo 를 옮겨도 항상 형제 `summaries/` 로 감. `YT_OUT_DIR` 가 우선.
- stem = `{date}_{safe(title,60)}_{VID}` — VID 로 동일자 충돌 방지. `_transcripts/`(언더스코어)는 도메인 목록에서 제외.

## 경로 안전 (핵심 — 바꿀 때 주의)

**모든 파일시스템 쓰기와 경로 결정은 `yt-script` 안에서 결정론적으로** 일어난다. `--save` 는 (a) transcript 경로가 `OUT_DIR/_transcripts/` 내부인지 검증, (b) stem/out_dir 을 그 경로에서 역산, (c) 도메인만 정규화(NFC·허용문자 `[가-힣A-Za-z0-9_-]`·`/`·`..` 제거·길이≤30·빈값→`미분류`). Claude 는 도메인명과 요약 텍스트만 넘긴다 → 자막發 경로 탈출 불가. frontmatter 헤더는 **표시용 힌트**일 뿐 안전에 의존하지 않는다(신뢰값은 파일 경로 자체).

## Exit code contract (바꾸지 말 것)

`yt-script` exit code 는 `yt.md` 예외 분기와 1:1이다:

- `1` 인자 없음 · `127` yt-dlp **또는 ytclean.py** 미발견
- `2` 자막 없음 (비공개·지역제한 포함)
- `3` 차단/오류 (다운로드 로그를 `403|ipblock|requestblock|sign in|bot` grep)

## Commands

```bash
./install.sh                       # 1회 셋업(idempotent): yt-dlp 확인 + yt-script·ytclean.py 심링크 + PATH
yt-script <URL> [lang=ko]          # 추출만. 결과: ../summaries/_transcripts/{stem}.txt + 클립보드
YT_OUT_DIR=~/Desktop/자막 yt-script <URL>   # 출력 폴더 변경
python3 ytclean.py <vtt> [chapters_json]    # 정리 로직 단독 실행(fixture 검증용)
export YT_PUBLISH_DIR=~/Desktop/dev-lab/study   # 발행 루트(외부 git repo 안, 주제 폴더들의 상위)
yt-script --topics                          # 발행 루트의 기존 주제 폴더 목록
yt-script --ls <topic>                      # 그 주제 폴더의 기존 파일명
yt-script --latest                          # 가장 최근 요약본 경로
yt-script --publish <summary_md> <topic> <filename>   # 그 폴더에 그 이름으로 발행(보통 /yt-push 가 판단해 호출)
```

테스트 스위트는 없다. **결정론 로직(`ytclean.py`)은 저장한 샘플 VTT/챕터JSON 으로 직접 검증**하고, 경로 안전은 `--save` 에 악성 도메인(`../../etc` 등)을 넣어 확인한다. 네트워크 의존(추출·차단)은 실제 URL 로 smoke 1회.

## Gotchas

- **유튜브 봇탐지가 자주 바뀐다.** 깨지면 코드보다 먼저 `yt-dlp -U`(brew면 `brew upgrade yt-dlp`)를 의심. 클라우드/공용 IP 는 403 잦고 가정용 IP 로컬 맥이 성공률 높다.
- **macOS 기본 bash 는 3.2** — `mapfile`/연관배열/`${v,,}` 등 bash4 문법 없음. `yt-script`·`install.sh` 수정 시 POSIX 수준으로(라인 파싱은 `sed`/`printf` 사용).
- **경로 포함 검사는 양쪽 다 realpath.** macOS `/var`↔`/private/var` 심링크 탓에 `--save` 의 `OUT_DIR/_transcripts` 와 입력 경로를 둘 다 `os.path.realpath` 해야 정상 비교된다(안 하면 정상 입력도 거부됨).
- **yt-dlp 메타는 한 호출로 묶는다.** title·id·chapters 를 `--print` 3개로 한 번에 받아 네트워크 왕복(=차단 위험)을 줄인다. 필드 추가 시 호출을 늘리지 말 것.
- `OUTPUT_FILE:`/`SAVED_FILE:` 마커 형식을 바꾸면 `yt.md` 가, `PUSHED_FILE:`/`COMMITTED_FILE:` 는 `yt-push.md` 가 깨진다. 마커와 슬래시 커맨드를 같이 고친다.
- **발행 위치 판단은 Claude(`/yt-push`), 경로 안전·git 은 yt-script.** `--save` 와 같은 분업 — Claude 는 `topic`(폴더명)만 넘기고, yt-script 가 정규화·경로조립·커밋·푸시. **자막/제목/본문이 폴더 경로를 직접 정하지 못한다**(topic 도 정규화돼 경로탈출 불가). `/yt-push` 는 `--topics` 출력의 **기존 폴더명을 그대로 재사용**해야 새 변종 폴더(`claude-code` vs `Claude_Code`)가 안 생긴다 — 이 규칙을 yt-push.md 가 명시한다.
- **발행 모드는 `OUT_DIR`(읽기) 와 `YT_PUBLISH_DIR`(쓰기) 가 다르다.** 입력 요약본은 OUT_DIR 내부인지 검증하고, 출력은 외부 repo 안 `{topic}/` 로 *의도적으로* 나간다. `YT_PUBLISH_DIR` 는 **발행 루트**(주제 폴더들의 상위, 예 `…/study`)이고 개인 환경값이라 **코드/공개 repo 에 하드코딩하지 말 것**(env 로만). repo 존재 확인은 가장 가까운 존재 상위 폴더에서 `git rev-parse --show-toplevel` 로 하고 루트/주제 폴더는 자동 생성한다.
- `yt-push.md` `allowed-tools` 는 `Bash(yt-script:*), Read`(내용 파악용 Read + 발행은 `yt-script` 가 git 실행 → Write/Bash(git) 불필요). 조회 마커(`LATEST_FILE:`/`PUBLISH_ROOT:`/`TOPICS:`/`FILES:`)를 바꾸면 yt-push.md 가 깨진다.
- `latest_md()` 는 `find|xargs stat -f '%m %N'|sort` 로 최근 .md 를 고른다 — `xargs ls` 는 **빈 입력 때 cwd 를 뒤지는 버그**가 있어 쓰지 말 것(stat 방식은 빈 입력 시 빈 출력).
- `ytclean.py` 는 **심링크로 실행돼도** 찾도록 yt-script 가 realpath 로 자기 경로를 역산해 옆에서 호출한다 + install 이 `~/bin` 에도 심링크한다(이중). 위치 로직을 바꾸면 둘 다 확인.
- `yt.md` `allowed-tools` 는 `Bash(yt-script:*), Read` 로 한정(저장도 `--save` 라 Write 불필요). 넓힐 때 의도 확인.
- 저장은 **heredoc** 으로 `yt-script --save` 에 stdin 전달 — `printf | …` 는 allowed-tools 위반.

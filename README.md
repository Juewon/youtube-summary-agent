# yt_summary_agent

유튜브 URL만 주면 **자막을 추출해 주제별로 구조화 요약**하고, 도메인별 폴더에 `.md` 로 저장하는 개인 에이전트.
자막을 손으로 복붙할 필요 없이, Claude Code 가 CLI(`yt-script`)를 직접 돌려 자막을 만들고 그 파일을 읽어 요약한 뒤
다시 `yt-script --save` 로 저장한다.

> 요약·도메인 판단 두뇌는 **Claude Code 자체**다(별도 LLM API 키 불필요). 파일쓰기·경로 안전은 `yt-script` 가 맡는다.
> 이 폴더는 도구(`yt-script`, `ytclean.py`)와 슬래시 커맨드(`yt.md`)의 **소스 of truth**이고,
> 전역 위치(`~/bin`, `~/.claude/commands`)에는 심링크로 연결된다.

## 무엇으로 요약하나 (사용 기술)

핵심 아이디어는 단순하다. **유튜브 영상에는 사람이 말한 내용이 "자막(스크립트)" 으로 들어 있다.** 그 자막 텍스트만 뽑아내면, 영상을 처음부터 볼 필요 없이 글로 요약할 수 있다. 그래서 이 프로젝트는 **① 자막을 뽑아내는 일** 과 **② 그 자막을 읽고 요약하는 일** 을 나눠서, 각 단계에 맞는 도구를 하나씩 쓴다.

아래는 각 도구가 *무엇이고* 여기서 *왜 쓰는지*를 풀어 쓴 것이다.

#### 1. yt-dlp — 유튜브에서 자막을 내려받는 프로그램
`yt-dlp` 는 유튜브 같은 사이트에서 영상·자막을 다운로드해 주는 **무료 오픈소스 명령줄 도구**다(유명한 `youtube-dl` 의 후속작). 여기서는 영상 자체는 받지 않고 **자막 텍스트와 제목·챕터 정보만** 골라 받는다. 사람이 직접 단 자막이 있으면 그걸, 없으면 유튜브가 자동 생성한 자막을 가져온다.
→ *직접 설치 필요:* `brew install yt-dlp` (아래 [설치] 참고)

#### 2. Python 스크립트 (`ytclean.py`) — 자막을 읽기 좋게 다듬는 단계
yt-dlp 가 받아온 자막은 `00:01:23.456 --> 00:01:25.789` 같은 **시간 표시와 중복 문장**이 잔뜩 섞인 날것의 형태(VTT 형식)다. 이 파이썬 스크립트가 그 군더더기를 걷어내고, 영상의 챕터(구간)별로 내용을 묶어 **사람이 읽을 수 있는 깔끔한 텍스트 파일** 로 정리한다. 파이썬은 맥에 기본 설치돼 있어 따로 준비할 게 거의 없다.

#### 3. Bash 스크립트 (`yt-script`) — 전체 과정을 묶어 돌리는 "리모컨"
위 1·2번을 사람이 매번 손으로 실행하긴 번거롭다. `yt-script` 는 **"유튜브 주소를 받으면 → yt-dlp 로 자막을 받고 → 파이썬으로 정리하고 → 정해진 폴더에 저장"** 하는 일련의 과정을 자동으로 이어 주는 셸(터미널) 스크립트다. 파일을 어디에 어떤 이름으로 저장할지, 엉뚱한 경로에 쓰지 않을지 같은 **안전·반복 작업**을 전담한다.

#### 4. Claude Code — 실제로 "요약" 을 하는 두뇌 (LLM)
여기까지는 자막을 *가져와 정리* 했을 뿐, 요약은 아직 안 했다. **실제 요약은 Claude Code(=지금 이 AI 코딩 도구) 가 직접 한다.** 정리된 자막 파일을 Claude 가 읽어서 **주제별로 구조화한 한국어 요약** 을 만들고, 어떤 폴더(도메인)에 넣을지까지 판단한다.
→ 별도의 요약 API 나 결제가 **필요 없다.** 챗GPT 같은 외부 서비스에 자막을 붙여넣는 대신, 코딩에 쓰는 Claude 가 그 자리에서 요약해 주는 구조다.

#### 5. `/yt` 슬래시 커맨드 — 위 전부를 한 줄로
매번 단계를 떠올릴 필요 없이, Claude Code 에 `/yt <유튜브주소>` 한 줄만 입력하면 **추출 → 정리 → 요약 → 저장** 이 한 번에 돌아간다. (`yt.md` 파일이 이 명령의 정의서다.)

> **한 줄 요약:** 자막을 *가져오고 다듬는 기계적인 일* 은 yt-dlp·파이썬·셸 스크립트가 하고, *읽고 요약하는 판단의 일* 은 Claude(LLM) 가 한다. 이렇게 역할을 나눈 게 이 프로젝트의 핵심이다.

## 동작 흐름
```
Claude Code 에 URL 전달
  → yt-script 실행 (yt-dlp 로 자막 추출, ytclean.py 로 챕터 구간별 정리)
  → _transcripts/{날짜}_{제목}_{VID}.txt 의 OUTPUT_FILE 경로를 Claude Code 가 Read
  → 주제별로 구조화해 한국어 요약 + 도메인 결정
  → yt-script --save 로 {도메인}/{stem}.md 저장
```

## 폴더 구조
```text
yt_summary_agent/
├─ README.md       # 이 문서
├─ install.sh      # 1회 셋업 (yt-dlp 설치 + 전역 심링크 + PATH)
├─ yt-script       # 자막 추출 + 요약 저장 CLI (bash)
├─ ytclean.py      # VTT 정리 + 챕터 구간 버킷팅 (python3, 단위테스트 대상)
└─ yt.md           # /yt 슬래시 커맨드 소스
```

## 사전 요구
- macOS, zsh
- `yt-dlp` (자막 추출). 자막만 받으므로 ffmpeg 는 불필요.
- `python3` (자막 정리 — 시스템 python3 로 동작)

## 설치 (한 번만)
```bash
cd /Users/seednpc09/Desktop/04_Agents/youtube/yt_summary_agent
./install.sh
source ~/.zshrc      # 현재 터미널에 PATH 즉시 적용
```
`install.sh` 가 하는 일: yt-dlp 설치 확인/설치 · `~/bin/yt-script`·`~/bin/ytclean.py` 심링크 · `~/bin` PATH 등록 ·
`~/.claude/commands/yt.md` 심링크. 여러 번 실행해도 안전(idempotent).

## 사용법
### Claude Code 에서 (추천)
```
/yt https://youtu.be/XXXXXXXXXXX          # 한국어 영상
/yt https://youtu.be/XXXXXXXXXXX en       # 영어 영상
```
또는 자연어로: `이 영상 핵심만 정리해줘: https://youtu.be/XXXX`

### 터미널에서 (자막 텍스트만)
```bash
yt-script https://youtu.be/XXXX           # _transcripts/{날짜}_{제목}_{VID}.txt 생성 + 클립보드 복사
yt-script https://youtu.be/XXXX en        # 언어 지정
YT_OUT_DIR=~/Desktop/자막 yt-script <URL>  # 출력 폴더 변경
```
요약 `.md` 저장은 Claude Code 가 `/yt` 안에서 `yt-script --save <transcript> <도메인>`(요약을 stdin 으로) 형태로 호출한다.

## 출력
| 항목 | 위치 |
|------|------|
| 자막 원본 `.txt` | `{출력}/_transcripts/{날짜}_{제목}_{VID}.txt` |
| 구조화 요약 `.md` | `{출력}/{도메인}/{날짜}_{제목}_{VID}.md` |

기본 `{출력}` 은 **소스 폴더의 형제 `summaries/`**(예: `04_Agents/youtube/summaries/`). `YT_OUT_DIR` 로 변경 가능.
| 클립보드 | 원문 자막을 시스템 클립보드에 자동 복사(best-effort) |

stdout 첫 줄의 `OUTPUT_FILE: <경로>` 가 Claude Code 가 읽을 자막 파일 경로다.
파일명에 **영상 ID(VID)** 가 들어가 같은 날 동명 영상이 충돌하지 않는다. 도메인 폴더명은 저장 시 정규화된다(허용 문자만, 빈 결과는 `미분류`).

## 알려진 한계
- 플레이리스트 URL 은 `--no-playlist` 로 **첫 영상 한 편만** 처리한다.
- 라이브/프리미어·연령제한·로그인 필요 영상은 보통 자막 추출 단계에서 실패한다(exit 2/3).
- 영어 자막만 있는 영상도 요약은 한국어로 만든다(`lang_used` 헤더로 어떤 자막을 썼는지 표시).

## 트러블슈팅
| 증상 | 원인 | 해결 |
|------|------|------|
| `자막 없음` (exit 2) | 영상에 자막 없음(비공개·지역제한 포함) | 유튜브 "··· → 스크립트 표시"로 직접 복사 |
| `차단/오류` `403`/`IpBlocked` (exit 3) | 유튜브 IP 차단(요청 과다·클라우드 IP) | `yt-dlp -U` (brew면 `brew upgrade yt-dlp`) 후 잠시 뒤 재시도. 가정용 IP 로컬 맥에서 성공률 높음 |
| `command not found: yt-script` | PATH 미적용 | `source ~/.zshrc`, `~/bin/yt-script` 존재 확인 |
| `ytclean.py 를 찾을 수 없습니다` (exit 127) | 심링크 누락 | `./install.sh` 재실행 (`~/bin/ytclean.py` 생성) |
| `yt-dlp 가 설치돼 있지 않습니다` (exit 127) | yt-dlp 미설치 | `brew install yt-dlp` |
| 텍스트에 같은 문구가 약간 반복 | 자동자막의 롤링 특성(일부는 정리됨) | 요약에는 영향 없음 — 그대로 진행 |

## 유지보수
유튜브가 내부 구조/봇탐지를 자주 바꾼다. 잘 되던 게 안 되면 먼저 업데이트:
```bash
yt-dlp -U            # Homebrew 설치본이면: brew upgrade yt-dlp
```

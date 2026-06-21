#!/usr/bin/env python3
"""yt-script 보조 모듈 — VTT 자막을 정리하고 챕터 구간별 섹션 '본문'을 만든다.

사용법: ytclean.py <vtt_path> [chapters_json]
출력:   본문 텍스트(stdout). frontmatter 헤더는 호출자(yt-script)가 붙인다.

- 챕터 JSON 이 파싱 실패/빈값/타임스탬프 전무이면 챕터 없이 평문으로 폴백한다.
- 함수 단위로 import 해 fixture 테스트할 수 있다(clean_cues / load_chapters / build_body).
"""
import sys
import re
import json


def parse_ts(ts):
    """'HH:MM:SS.mmm' / 'MM:SS.mmm' / ',' 밀리초 구분 -> 초(float). 실패 시 None."""
    m = re.match(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?", ts.strip())
    if not m:
        return None
    h = int(m.group(1) or 0)
    mm = int(m.group(2))
    ss = int(m.group(3))
    ms = int((m.group(4) or "0").ljust(3, "0"))
    return h * 3600 + mm * 60 + ss + ms / 1000.0


def clean_cues(raw):
    """VTT 원문 -> [(start_sec|None, text), ...] 정리된 줄 목록.

    타임코드/cue번호/인라인태그 제거, 연속 완전중복 제거.
    롤링 중복 머지는 merge_rolling 에서 (챕터 버킷 단위로) 따로 수행한다 —
    그래야 챕터 경계를 넘나드는 자막이 엉뚱한 챕터로 합쳐지지 않는다.
    """
    cur_start = None
    rows = []  # (start, text)
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s == "WEBVTT":
            continue
        if s.startswith(("Kind:", "Language:", "NOTE")):
            continue
        if "-->" in s:                       # 타임코드 줄 -> 시작초 갱신
            cur_start = parse_ts(s.split("-->")[0])
            continue
        if re.fullmatch(r"\d+", s):          # cue 번호
            continue
        s = re.sub(r"<[^>]+>", "", s)        # 인라인 태그/타임스탬프 제거
        s = re.sub(r"\s+", " ", s).strip()
        if not s:
            continue
        if rows and rows[-1][1] == s:        # 연속 완전중복
            continue
        rows.append((cur_start, s))
    return rows


def merge_rolling(rows):
    """자동자막 롤링 중복(직전 줄이 현재 줄에 포함/반대) 머지.

    더 긴 쪽 유지, 병합 그룹의 가장 이른 시작초 유지.
    """
    merged = []
    for start, s in rows:
        if merged and (s in merged[-1][1] or merged[-1][1] in s):
            prev_start, prev_s = merged[-1]
            keep_text = s if len(s) > len(prev_s) else prev_s
            starts = [x for x in (prev_start, start) if x is not None]
            keep_start = min(starts) if starts else None
            merged[-1] = (keep_start, keep_text)
            continue
        merged.append((start, s))
    return merged


def load_chapters(chapters_json):
    """JSON 문자열 -> [(start_sec, title), ...] (시작초 오름차순). 실패/빈 -> []."""
    if not chapters_json:
        return []
    try:
        data = json.loads(chapters_json)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list) or not data:
        return []
    chaps = []
    for c in data:
        if not isinstance(c, dict):
            continue
        st = c.get("start_time")
        if st is None:
            continue
        try:
            st = float(st)
        except (ValueError, TypeError):
            continue
        title = (c.get("title") or "").strip() or "(제목 없음)"
        chaps.append((st, title))
    chaps.sort(key=lambda x: x[0])
    return chaps


def fmt_ts(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build_body(rows, chaps):
    """정리된 (start,text) 줄 + 챕터 -> 본문 텍스트.

    챕터가 없거나 줄에 시작초가 전무하면 평문으로 폴백.
    버킷 경계 [start_i, start_{i+1}) (end_time 무시, 마지막 open-ended).
    첫 챕터 시작 이전 줄은 '인트로' 섹션으로.
    롤링 중복 머지는 각 버킷(인트로/챕터) 안에서 수행해 경계 오귀속을 막는다.
    """
    if not chaps or not any(start is not None for start, _ in rows):
        plain = "\n".join(t for _, t in merge_rolling(rows))
        return (plain + "\n") if plain else ""

    bounds = [st for st, _ in chaps]

    def bucket_of(start):
        if start is None:
            return None
        idx = None
        for i, b in enumerate(bounds):
            if start >= b:
                idx = i
            else:
                break
        return idx  # None -> 첫 챕터 이전(인트로)

    intro_rows = []
    bucket_rows = [[] for _ in chaps]
    for start, text in rows:
        bi = bucket_of(start)
        if bi is None:
            intro_rows.append((start, text))
        else:
            bucket_rows[bi].append((start, text))

    out = []
    intro = [t for _, t in merge_rolling(intro_rows)]
    if intro:
        out.append("## [00:00] 인트로")
        out.append("\n".join(intro))
        out.append("")
    for (st, title), brows in zip(chaps, bucket_rows):
        lines = [t for _, t in merge_rolling(brows)]
        out.append(f"## [{fmt_ts(st)}] {title}")
        out.append("\n".join(lines) if lines else "(이 구간 자막 없음)")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: ytclean.py <vtt_path> [chapters_json]\n")
        return 1
    sub_path = argv[1]
    chapters_json = argv[2] if len(argv) > 2 else ""
    with open(sub_path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    rows = clean_cues(raw)
    chaps = load_chapters(chapters_json)
    sys.stdout.write(build_body(rows, chaps))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

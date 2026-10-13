# 다운힐 도미네이션 · PS2 북미판 한글 패치 v1.0

대상: **Downhill Domination (USA), SCUS-97177**

비공식 팬 한글 패치입니다. 적법하게 보유한 북미판 원본 ISO에 xdelta 패치를 적용해 사용합니다.
릴리즈 첨부 파일은 xdelta와 PCSX2용 와이드 패치(pnach)이며 원본·완성 ISO, 게임 파일, 폰트는 배포하지 않습니다.

## 패치 적용

| 파일 | SHA-256 |
|---|---|
| 원본 `Downhill Domination (USA).iso` (2,530,869,248바이트) | `0fe2b77713d3440cc3030741ea0b18f49e3feaa09671a30a421e0d4888a7eb86` |
| 완성 `Downhill Domination (Korean).iso` (2,556,844,032바이트) | `ba65e21202abe1fa682239d6ad877728bc4f2694425724697cdca34d94f6be0c` |
| `Downhill_Domination_PS2_KO_v1.0.xdelta` | `1fb80ff5f4d081d353b9e44115309d203e285730578909abf6943eec06756d0f` |

```powershell
xdelta3 -d -s ".\Downhill Domination (USA).iso" .\Downhill_Domination_PS2_KO_v1.0.xdelta ".\Downhill Domination (Korean).iso"
```

## 16:9 와이드 패치

한글 패치는 실행 파일을 수정하므로 게임 CRC가 원본(5AE01D98)과 달리 **32892A4E**가 됩니다. 그래서 PCSX2에
내장된 원본용 와이드 패치는 자동으로 적용되지 않습니다. 릴리즈에 한글판 CRC용 `SCUS-97177_32892A4E.pnach`를
함께 첨부합니다(PCSX2 커뮤니티 패치를 그대로 옮기고 파일 이름·CRC만 맞춤).
사용법은 [docs/WIDESCREEN.md](docs/WIDESCREEN.md)를 보세요.

## 번역 범위

- 메뉴·옵션, 바이크 숍, 커리어·레이스 메시지, 레이스 중 알림(격투·아이템·손상), 트레이닝 설명, 라이더 소개
  (키·몸무게는 cm/kg 환산), 해금 조건, 메모리 카드 안내, 하단 버튼 안내 등 약 1,170개 문자열.
- 외부 번역기·기계 번역 없이 직접 번역했습니다. 용어는 [translation/glossary.md](translation/glossary.md) 기준.
- 메뉴 항목은 화면 폭을 고려해 띄어쓰기 없이 붙여 썼습니다(예: 싱글플레이어).

## 한글 표시 방식

1. **인코딩**: 한글은 2바이트(선두 0xF0~0xF6, 후속 0xA0~0xFF, 최대 672자, 현재 445자). 0x80~0x9F 는 버튼 아이콘 대역이라 피했다.
2. **폰트 텍스처**: 원본 폰트는 512×512 PSMT4HL(24비트 화면 버퍼의 비트 24~27). 같은 VRAM 위치의 비트 28~31(PSMT4HH)이
   비어 있어 여기에 한글 페이지를 둔다. 폰트가 든 RTX(상주 텍스처) 128개(SHELL/UI, 레벨 54개, 로딩 화면 73개)에 4HH 레코드
   3개(ID 997~999)를 추가한다. 일부 레벨이 위 64줄의 HH 를 쓰므로 한글은 y=65부터 21px 셀(24×21=504칸)에 배치.
   서체는 나눔스퀘어 네오 ExtraBold, 원본처럼 흰 채움 + 검은 2px 외곽선 + 기울임, 원본 CLUT 그대로.
3. **ELF 코드**: drawString 의 일반 문자 분기(0x20FD68)와 폭 측정(0x20F944)을 훅으로 바꿔 2바이트를 해석하고, 한글 글자는
   GIF REGLIST [TEX0(4HH), UV, XYZ3, UV, XYZ2, TEX0(원래)] 로 따로 그린다(TEX0 는 현재 폰트 TEX0 에서 PSM 만 교체).
   그린 뒤 배치 상태를 3으로 둬, 상태 1일 때 직전 qword 를 되감아 덮어쓰는 색 변경 함수와 충돌하지 않게 했다.
4. **문자열 배치**: 들어가면 제자리, 아니면 무동작 printf 전용 디버그 문자열·북미판 미사용 외국어 문자열(포인터는 영어 쪽으로
   돌림)·비워진 원래 자리로 재배치하고 포인터/lui-addiu 참조를 고친다. 이름이 고정 위치에 덧씌워지는 메시지("…당함:")는
   접두부 길이를 원문과 같게 맞췄다. PCSX2 는 두 번째 PT_LOAD 를 적재하지 않아 기존 세그먼트 안에서만 처리.

## 검증

- PCSX2 2.2: 부팅, 타이틀 메뉴, 게임 모드·레이스 선택, 라이더 선택·소개, 바이크 숍, 레벨 선택·로딩, 레벨 진입 문구,
  레이스 HUD, 일시정지 메뉴, 16:9 와이드 패치 적용.
- 공개 소스 재빌드 결과와 xdelta 복원 ISO SHA-256 일치.
- **미검증**: 전체 플레이, 멀티플레이, 저장/불러오기, 실기.

## 영어로 남은 부분

게임 로고, 이미지로 된 글자(BIKE SHOP, BIKE / JERSEY 등), 라이더 이름, 바이크·부품·스폰서 브랜드, 트릭 이름,
노래 제목·아티스트, 메모리 카드 세이브 파일 제목, 제작진 크레딧.

## 저장소 구성

- `translation/ko_*.tsv`: ELF 내 문자열 위치(16진) + 한국어(영어 원문 미포함, 원문은 원본 ISO에서 읽음)
- `tools/`: 빌드·분석 도구, 재빌드는 [docs/BUILD.md](docs/BUILD.md)
- `widescreen/`: PCSX2 16:9 와이드 패치
- 권리 고지 [RIGHTS.md](RIGHTS.md), 변경 내역 [CHANGELOG.md](CHANGELOG.md)

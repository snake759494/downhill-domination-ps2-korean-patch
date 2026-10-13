# 다운힐 도미네이션 PS2 북미판 한글 패치 v1.0

SCUS-97177 북미 원본용 정식 한글 패치입니다. 첨부 파일은 한글 패치 xdelta와 PCSX2 16:9 와이드 패치 pnach이며, 원본 ISO·게임 파일·폰트는 제공하지 않습니다.

- 메뉴·옵션, 바이크 숍, 커리어·레이스 메시지, 레이스 중 알림(격투·아이템·손상), 트레이닝 설명, 라이더 소개, 해금 조건, 메모리 카드 안내, 하단 버튼 안내 등 약 1,170항목 한글화(외부 기계 번역 미사용).
- 영문 전용 엔진의 글자 출력 루틴에 2바이트 한글 처리를 추가하고, 원본 폰트 텍스처와 같은 VRAM 위치의 빈 4비트(PSMT4HH)에 한글 445자(나눔스퀘어 네오, 원본처럼 외곽선·기울임)를 넣었습니다. 메뉴·레벨·로딩 화면 모두 적용.
- 라이더 이름, 바이크·부품·스폰서 브랜드, 트릭 이름, 노래 제목·아티스트, 이미지 속 글자는 원문 유지.
- PCSX2에서 부팅·타이틀 메뉴·게임 모드/레이스 선택·라이더 선택/소개·바이크 숍·레벨 선택·레벨 로딩·레벨 진입 문구·레이스 HUD·일시정지·와이드 패치 확인, 공개 소스 재빌드 및 xdelta 복원 해시 일치. 전체 플레이, 멀티플레이, 저장/불러오기, 실기는 미검증입니다.

## 첨부 파일

- `Downhill_Domination_PS2_KO_v1.0.xdelta`: 한글 패치(북미 원본 ISO용)
- `SCUS-97177_32892A4E.pnach`: PCSX2 16:9 와이드 패치(한글판 CRC 32892A4E용, PCSX2 커뮤니티 패치를 그대로 옮김)

## 한글 패치 적용

1. xdelta3(또는 xdeltaUI)를 준비합니다.
2. 원본 `Downhill Domination (USA).iso`의 SHA-256이 아래 값과 같은지 확인합니다.
3. 명령: `xdelta3 -d -s "Downhill Domination (USA).iso" Downhill_Domination_PS2_KO_v1.0.xdelta "Downhill Domination (Korean).iso"`
   - xdeltaUI: Patch에 xdelta, Source File에 원본 ISO, Output File에 만들 ISO 이름을 넣고 Patch를 누릅니다.

## 16:9 와이드 패치 사용법

한글 패치는 실행 파일을 수정해 게임 CRC가 원본 5AE01D98에서 **32892A4E**로 바뀝니다. PCSX2 내장 와이드 패치는 CRC로 찾으므로 한글판에는 자동 적용되지 않아, 한글판 CRC용 파일을 첨부했습니다.

**PCSX2 2.x(권장)**
1. 첨부한 `SCUS-97177_32892A4E.pnach`를 `문서\PCSX2\patches\`(포터블은 `PCSX2 폴더\patches\`)에 넣습니다.
2. 게임 목록에서 Downhill Domination을 오른쪽 클릭 → 속성 → **패치** 탭 → **Widescreen 16:9** 체크.
3. 화면 비율은 패치가 자동으로 16:9로 바꿉니다. 수동 지정 시 속성 → 그래픽 → 디스플레이에서 화면 비율 **16:9**, FMV 화면 비율 전환 **4:3**(동영상은 원래 4:3).
4. 게임 시작 시 “1개의 게임 패치가 활성화되었습니다” 표시 확인.

설정 파일로 켜려면 `문서\PCSX2\gamesettings\SCUS-97177_32892A4E.ini`에 다음을 저장합니다.

```ini
[Patches]
Enable = Widescreen 16:9

[EmuCore/GS]
AspectRatio = 16:9
FMVAspectRatioSwitch = 4:3
```

**PCSX2 1.6** — 파일 이름을 `32892A4E.pnach`로 바꿔 `cheats_ws` 폴더에 넣고, 시스템 → 와이드스크린 패치 사용을 켠 뒤 비디오 → 창 설정에서 16:9를 고릅니다.

로딩 화면은 원작 패치에서 해당 항목이 꺼져 있어 4:3으로 나옵니다. 끄려면 패치 탭 체크를 해제합니다. 원본(영문) ISO에는 PCSX2 내장 패치를 쓰면 됩니다. 자세한 내용은 저장소의 docs/WIDESCREEN.md를 보세요.

원본 SHA-256: `0fe2b77713d3440cc3030741ea0b18f49e3feaa09671a30a421e0d4888a7eb86`

완성 ISO SHA-256: `ba65e21202abe1fa682239d6ad877728bc4f2694425724697cdca34d94f6be0c`

xdelta SHA-256: `1fb80ff5f4d081d353b9e44115309d203e285730578909abf6943eec06756d0f`

와이드 패치 SHA-256: `3918060366b45cb902c49ce175372fe8ef70d9e298b3b6f9d30fbacd52b5aa6c`

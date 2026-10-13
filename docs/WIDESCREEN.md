# PCSX2 16:9 와이드 패치 사용법

`SCUS-97177_32892A4E.pnach`는 PCSX2 커뮤니티 패치 모음(PCSX2 2.x에 `resources/patches.zip`으로 포함)의
Downhill Domination 와이드 패치(`SCUS-97177_5AE01D98.pnach`, 작성자 Aced14)를 그대로 옮긴 것입니다.

**왜 따로 필요한가:** 한글 패치는 실행 파일(SCUS_971.77)을 수정하므로 PCSX2가 계산하는 게임 CRC가
원본 **5AE01D98**에서 **32892A4E**로 바뀝니다. PCSX2 내장 패치는 CRC로 찾기 때문에 한글판에는 자동으로 붙지 않습니다.
패치가 고치는 주소 31곳은 한글판 실행 파일에서도 원본 값 그대로라(한글 패치와 겹치지 않음) 내용은 그대로 쓸 수 있습니다.

- 3D 화면(메뉴 배경, 레이스, 리플레이, 2~4인 분할 화면)의 시야각을 넓혀 16:9로 보여 줍니다.
- 바이크 숍 고글 화면 HUD 폭 보정 포함. 로딩 화면 항목은 원작 패치에서 꺼져 있어 로딩 화면은 4:3(좌우 검은 띠)입니다.
- 같은 파일의 `No-Interlacing`은 선택 사항입니다(원본 패치 그대로, 한글판에서는 미검증).

## PCSX2 2.x (Qt) — 권장

1. 첨부한 `SCUS-97177_32892A4E.pnach`를 PCSX2 사용자 폴더의 `patches` 폴더에 넣습니다.
   - 설치판: `문서\PCSX2\patches\`
   - 포터블판: `PCSX2 폴더\patches\`
2. PCSX2 게임 목록에서 **Downhill Domination**(한글 ISO)을 오른쪽 클릭 → **속성(Properties)**.
3. **패치(Patches)** 탭에서 **Widescreen 16:9**에 체크합니다(목록에 없으면 1단계 폴더와 파일 이름을 확인).
4. 화면 비율은 패치가 자동으로 16:9로 바꿉니다(`gsaspectratio=16:9`). 수동으로 정하려면
   **그래픽(Graphics) → 디스플레이(Display) → 화면 비율(Aspect Ratio)**을 **16:9**로,
   **FMV 화면 비율 전환(FMV Aspect Ratio Override)**은 **4:3**으로 둡니다(동영상은 원래 4:3).
5. 게임을 시작하면 화면에 “1개의 게임 패치가 활성화되었습니다”가 표시됩니다.

설정 파일로 켜려면 `문서\PCSX2\gamesettings\SCUS-97177_32892A4E.ini`에 다음 내용을 저장합니다.

```ini
[Patches]
Enable = Widescreen 16:9

[EmuCore/GS]
AspectRatio = 16:9
FMVAspectRatioSwitch = 4:3
```

## PCSX2 1.6 (wxWidgets)

1. `SCUS-97177_32892A4E.pnach` 이름을 `32892A4E.pnach`로 바꿔 `cheats_ws` 폴더에 넣습니다.
2. **시스템(System) → 와이드스크린 패치 사용(Enable Widescreen Patches)**을 켭니다.
3. **설정(Config) → 비디오(Video) → 창 설정(Window Settings)**에서 화면 비율을 16:9로 바꿉니다.

## 참고

- 원본(영문) ISO에는 PCSX2 내장 패치(5AE01D98)를 쓰면 되며, 이 파일은 한글판 전용입니다.
- 끄려면 패치 탭의 체크를 해제하거나 위 `.ini`의 `Enable` 줄을 지웁니다.
- PCSX2 2.2에서 한글판에 적용되는 것을 확인했습니다(로그: `Enabled patch: Widescreen 16:9`,
  타이틀·모드 선택·바이크 숍·레벨 진입·레이스 HUD·일시정지 화면 정상).

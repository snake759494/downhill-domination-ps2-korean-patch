# 재빌드

Python 3.13에서 검증했습니다. 저장소 루트에 해시가 일치하는 원본을 `Downhill Domination (USA).iso`라는 이름으로 두고,
`NanumSquareNeo-dEb.ttf`를 루트에 별도로 준비합니다. 이 파일들은 Git에서 제외됩니다.

```powershell
python -m pip install -r requirements.txt
python -X utf8 tools/build.py      # 원본 ISO → Downhill Domination (Korean).iso
```

완성 ISO SHA-256은 README와 일치해야 합니다.

## 구성

- `tools/build.py`: 번역 인코딩, ELF 문자열 배치·재배치, 텍스트 루틴 훅, RTX 한글 레코드 추가, ISO9660/UDF 갱신
- `tools/asm.py`: 패치 코드용 소형 MIPS(R5900) 어셈블러
- `tools/kfont.py`: 한글 글리프 페이지(원본 CLUT, 외곽선·기울임) 생성
- `tools/ie.py`: `IE\x03\x04` 압축 컨테이너(ZIP 변형, deflate)
- `tools/rtx.py`: 상주 텍스처(RTX) 레코드
- `tools/udf.py`, `tools/iso.py`: 파일 레코드
- `tools/elf.py`, `tools/extract.py`, `tools/make_src.py`, `tools/strs.py`, `tools/gsmem.py`, `tools/gsparse.py`:
  분석용(문자열·참조 추출, GS 메모리/덤프 해석; 작업 폴더의 추출 파일 사용)
- `tools/emu.ps1`: PCSX2 자동 조작·캡처(작업 폴더의 전용 포터블 PCSX2, 자기 프로세스만 다룸)

## 패치 생성/복원

```powershell
xdelta3 -e -s "Downhill Domination (USA).iso" "Downhill Domination (Korean).iso" Downhill_Domination_PS2_KO_v1.0.xdelta
xdelta3 -d -s "Downhill Domination (USA).iso" Downhill_Domination_PS2_KO_v1.0.xdelta roundtrip.iso
```

xdelta 버전/옵션에 따라 패치 바이트는 달라질 수 있지만 복원 ISO는 같아야 합니다. 생성한 게임 자료나 폰트를 커밋하지 마세요.

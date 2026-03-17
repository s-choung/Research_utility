# Word 화학식 Subscript/Superscript 자동 수정

Word docx 파일 내 화학식의 subscript/superscript를 자동 수정하는 Python 스크립트.

## 설치

```bash
pip install python-docx lxml
```

## 사용법

```bash
# 원본 덮어쓰기 (백업 자동 생성: *_backup.docx)
python fix_chem_subscript.py input.docx

# 별도 파일로 저장
python fix_chem_subscript.py input.docx output.docx
```

## 지원 패턴

**Subscript (아래첨자):**

| 입력 | 결과 |
|------|------|
| MnO2 | MnO₂ |
| PtO2 | PtO₂ |
| CeO2 | CeO₂ |
| TiO2 | TiO₂ |
| PtF6 | PtF₆ |
| NH3 | NH₃ |
| O2 | O₂ |
| CO2 | CO₂ |
| H2O | H₂O |
| SO4 | SO₄ |

**Superscript (위첨자):**

| 입력 | 결과 |
|------|------|
| Pt6+ | Pt⁶⁺ |
| Fe3+ | Fe³⁺ |
| Co2+ | Co²⁺ |
| Mn4+ | Mn⁴⁺ |

## 동작 원리

1. `python-docx`로 docx 로드
2. 정규식으로 화학식 패턴 탐지
3. 해당 run을 split → 숫자/charge 부분에 XML `vertAlign` 속성 추가
4. 텍스트 내용은 변경 없음, 서식만 변경

## 패턴 추가

`fix_chem_subscript.py` 내 `COMBINED_RE`와 `PATTERN_DEFS`에 새 패턴 추가.

예: Al₂O₃ 지원 → `COMBINED_RE`에 `r'|Al\d+O\d+'` 추가 후 `PATTERN_DEFS`에 split 로직 추가.

## 주의사항

- 백업 파일이 자동 생성되므로 원본 손실 걱정 없음
- oMath(수식 객체) 내부 텍스트는 처리 안 됨

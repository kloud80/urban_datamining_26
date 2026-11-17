# -*- coding: utf-8 -*-
"""2040년 파주 도시기본계획 최종 보고서(2026.06, 721쪽, 약 66MB)를 내려받는다.

    python data/get_paju.py

출처: 파주시 홈페이지 > 도시계획 > 도시기본계획 > 2040년 파주 도시기본계획
      https://www.paju.go.kr/www/www_02/city/city_02/city_02_04/city_02_04_03.jsp
경기도가 2026.6.5 최종 승인했다. 원문은 저장소에 올리지 않는다(용량·재배포).
"""
import pathlib
import sys
import urllib.request

URL = ("https://www.paju.go.kr/webcontent/ckeditor/2026/7/23/"
       "9b7ae538-2f44-4777-90fa-a35f45652737.pdf")
OUT = pathlib.Path(__file__).resolve().parent / "paju_2040.pdf"

if OUT.exists() and OUT.stat().st_size > 50_000_000:
    print(f"이미 있다: {OUT.name} ({OUT.stat().st_size / 1e6:.1f}MB)")
    sys.exit()

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=120) as r, open(OUT, "wb") as f:
    total = int(r.headers.get("Content-Length", 0))
    got = 0
    while chunk := r.read(1 << 20):
        f.write(chunk)
        got += len(chunk)
        if total:
            print(f"\r{got / 1e6:5.1f} / {total / 1e6:.1f} MB", end="")
print(f"\n저장: {OUT}")

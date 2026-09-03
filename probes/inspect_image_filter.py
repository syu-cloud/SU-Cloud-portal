"""
Glance 이미지 카탈로그 조회 점검.

포털이 학생에게 보여줄 이미지를 골라내는 기준: tag = "su-portal"

[조사 결과 2026-09-03]
- CLI(`image list --property k=v`)는 동작하나 SDK에서는 무시됨(전량 반환)
  → property 필터 사용 불가
- SDK `images(tag=...)`는 서버측 필터로 정상 동작
  → tag 방식 채택

운영계 이관 시 동일 스크립트로 재확인함.
"""
import osclient

CATALOG_TAG = "su-portal"

conn = osclient.get_conn()

print("=== 1. 전량 조회 ===")
for img in conn.image.images():
    print(f"{img.name:16} tags={img.tags} status={img.status}")

print(f"\n=== 2. property 필터 — SDK에서 무시됨 (전량 반환 확인) ===")
r = list(conn.image.images(some_key="true"))
print(f"count={len(r)} -> {[i.name for i in r]}")

print(f"\n=== 3. tag 필터 — 채택 방식 ===")
r = list(conn.image.images(tag=CATALOG_TAG))
print(f"count={len(r)} -> {[i.name for i in r]}")

print("\n=== 4. 카탈로그 항목 상세 ===")
for img in conn.image.images(tag=CATALOG_TAG):
    print(f"{img.name:16} id={img.id} min_disk={img.min_disk} "
          f"min_ram={img.min_ram} visibility={img.visibility} status={img.status}")
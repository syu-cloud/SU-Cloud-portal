"""
tag + status 조합 필터 실측.

목적: osclient.image.list_by_tag()에 status="active"를 함께 넣을지 판정.
      tag 단독 동작은 확인했으나, 조합은 미검증임.

전제: su-img-test-1 을 일시적으로 deactivated 로 전환한 뒤 실행.
      검증 후 반드시 --activate 로 복구할 것.
"""
import osclient

TAG = "su-portal"
conn = osclient.get_conn()

print("=== 현재 상태 ===")
for img in conn.image.images():
    print(f"  {img.name:16} status={img.status:12} tags={img.tags}")

print("\n=== tag 단독 ===")
r = list(conn.image.images(tag=TAG))
print(f"count={len(r)} -> {[(i.name, i.status) for i in r]}")

print("\n=== tag + status=active ===")
r = list(conn.image.images(tag=TAG, status="active"))
print(f"count={len(r)} -> {[(i.name, i.status) for i in r]}")
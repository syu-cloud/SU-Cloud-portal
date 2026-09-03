"""tag + status 조합 필터 실측.

실행 전 su-img-test-1 을 --deactivate, 실행 후 --activate 로 복구.
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
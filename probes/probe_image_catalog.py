"""osclient.image 동작 검증."""
import osclient
from osclient import image as osimage

TAG = "su-portal"

conn = osclient.get_conn()

print("=== list_by_tag() ===")
items = osimage.list_by_tag(conn, TAG)
print(f"count={len(items)}")
for it in items:
    print(f"  {it['name']:16} min_disk={it['min_disk']:3} "
          f"visibility={it['visibility']:8} id={it['id']}")

print("\n=== 없는 태그 ===")
print(f"count={len(osimage.list_by_tag(conn, 'no-such-tag'))}")

print("\n=== get() — C-6 검증 조건 ===")
for target in ["ubuntu-24.04", "su-img-test-1", "cirros", "no-such-image"]:
    img = osimage.get(conn, target)
    if img is None:
        print(f"  {target:16} → 미존재")
        continue
    ok = img["status"] == "active" and TAG in img["tags"]
    print(f"  {target:16} status={img['status']:12} "
          f"tags={img['tags']} → {'허용' if ok else '거부'}")
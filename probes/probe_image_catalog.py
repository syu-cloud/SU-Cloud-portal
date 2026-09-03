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

print("\n=== get() — UUID ===")
print(osimage.get(conn, items[0]["id"]))

print("\n=== get() — 이름 ===")
print(osimage.get(conn, "ubuntu-24.04"))

print("\n=== get() — 없는 값 ===")
print(osimage.get(conn, "no-such-image"))
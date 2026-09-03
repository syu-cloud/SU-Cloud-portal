"""osclient.image 동작 검증."""
import osclient
from osclient import image as osimage

TAG = "su-portal"

conn = osclient.get_conn()

print("=== catalog() ===")
items = osimage.catalog(conn, TAG)
print(f"count={len(items)}")
for it in items:
    print(f"  {it['name']:16} min_disk={it['min_disk']:3} "
          f"visibility={it['visibility']:8} id={it['id']}")

print("\n=== catalog() — 없는 태그 ===")
print(f"count={len(osimage.catalog(conn, 'no-such-tag'))}")

print("\n=== get() — UUID ===")
print(osimage.get(conn, items[0]["id"]))

print("\n=== get() — 이름 ===")
print(osimage.get(conn, "ubuntu-24.04"))

print("\n=== get() — 없는 값 ===")
print(osimage.get(conn, "no-such-image"))
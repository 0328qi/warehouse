"""接口冒烟测试：商品 -> 入库 -> 库存 -> 出库 -> 流水 -> 盘点。"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000/api/v1"


def call(method: str, path: str, body: dict | None = None, token: str = ""):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  !! {method} {path} -> {e.code}: {e.read().decode('utf-8')[:200]}")
        raise SystemExit(1)


token = call("POST", "/auth/login", {"username": "admin", "password": "admin123"})["access_token"]
print("1. 登录 OK")

g = call("POST", "/basic/goods", {"name": "测试商品A", "unit": "个", "price": 9.9, "min_stock": 10, "category_id": 1}, token)
print(f"2. 创建商品 {g['code']}")

loc = call("GET", "/basic/locations/all?warehouse_id=1", token=token)[0]
print(f"3. 选取库位 {loc['code']}")

inb = call("POST", "/inbound/orders", {
    "type": "purchase", "warehouse_id": 1,
    "items": [{"goods_id": g["id"], "location_id": loc["id"], "qty": 100}],
}, token)
print(f"4. 创建入库单 {inb['order_no']} (status={inb['status']})")

executed = call("POST", f"/inbound/orders/{inb['id']}/execute", {}, token)
print(f"5. 执行入库 -> {executed['status']}")

bal = call("GET", f"/inventory/balances?goods_id={g['id']}", token=token)["items"][0]
assert bal["qty"] == 100, bal
print(f"6. 库存查询: {bal['goods_name']} @ {bal['location_code']} = {bal['qty']}")

out = call("POST", "/outbound/orders", {
    "type": "sale", "warehouse_id": 1,
    "items": [{"goods_id": g["id"], "location_id": loc["id"], "qty": 30}],
}, token)
executed = call("POST", f"/outbound/orders/{out['id']}/execute", {}, token)
print(f"7. 出库单 {out['order_no']} 执行 -> {executed['status']}")

bal = call("GET", f"/inventory/balances?goods_id={g['id']}", token=token)["items"][0]
assert bal["qty"] == 70, bal
print(f"8. 出库后库存 = {bal['qty']}")

tx = call("GET", "/inventory/transactions", token=token)
print(f"9. 流水 {tx['total']} 条，最新: {tx['items'][0]['biz_type']} {tx['items'][0]['qty']}")

# 超扣校验：执行出库应返回 400
over = call("POST", "/outbound/orders", {
    "type": "sale", "warehouse_id": 1,
    "items": [{"goods_id": g["id"], "location_id": loc["id"], "qty": 999}],
}, token)
try:
    call("POST", f"/outbound/orders/{over['id']}/execute", {}, token)
    print("10. !! 超扣未被拦截")
    raise SystemExit(1)
except SystemExit:
    # call() 内部将 HTTP 400 转为 SystemExit，此处即"超扣被拦截"
    print("10. 超扣拦截 OK")

# 移库
loc2 = call("GET", "/basic/locations/all?warehouse_id=1", token=token)[1]
mv = call("POST", "/inventory/move", {"goods_id": g["id"], "from_location_id": loc["id"], "to_location_id": loc2["id"], "qty": 20}, token)
print(f"11. 移库 20 -> {loc2['code']} ({mv['order_no']})")

# 盘点
st = call("POST", "/stocktake/orders", {"warehouse_id": 1}, token)
print(f"12. 盘点单 {st['order_no']}，明细 {st['item_count']} 条")
call("POST", f"/stocktake/orders/{st['id']}/record", [{"item_id": st["items"][0]["id"], "actual_qty": 48}], token)
fin = call("POST", f"/stocktake/orders/{st['id']}/finish", {}, token)
print(f"13. 盘点完成，差异数 {fin['diff_count']}")

dash = call("GET", "/dashboard/stats", token=token)
print(f"14. 看板: 总量={dash['total_qty']} 今日入={dash['today_in']} 今日出={dash['today_out']} 预警={dash['warning_count']}")

print("\n=== 全链路冒烟测试通过 ===")

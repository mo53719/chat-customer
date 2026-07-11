import sqlite3
conn = sqlite3.connect('data/chat_customer.db')
c = conn.cursor()
c.execute("SELECT id, role, length(content) FROM messages ORDER BY id DESC LIMIT 5")
rows = c.fetchall()
print("id | role | len | first80")
for r in rows:
    print(r[0], r[1], r[2])
c.execute("SELECT id, content FROM messages ORDER BY id DESC LIMIT 3")
for r in c.fetchall():
    cid, content = r
    print(f"--- id={cid} (len={len(content)}) ---")
    print(repr(content))

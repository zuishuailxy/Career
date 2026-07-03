import psycopg2

# 连接信息（替换为你的实际值）
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="mydatabase",
    user="admin",
    password="123456",
)
cur = conn.cursor()
# 执行建表语句
cur.execute("""
CREATE TABLE IF NOT EXISTS flowers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    country VARCHAR(50),
    price NUMERIC(10,2),
    weight NUMERIC(10,2),
    stock INT,
    sales INT,
    expiry_date DATE,
    description TEXT
);
""")
conn.commit()
flowers = [
    (
        "Rose",
        "Flower",
        "France",
        1.2,
        2.5,
        100,
        10,
        "2023-12-31",
        "A beautiful red rose",
    ),
    (
        "Tulip",
        "Flower",
        "Netherlands",
        0.8,
        2.0,
        150,
        25,
        "2023-12-31",
        "A colorful tulip",
    ),
    ("Lily", "Flower", "China", 1.5, 3.0, 80, 5, "2023-12-31", "An elegant white lily"),
    (
        "Daisy",
        "Flower",
        "USA",
        0.7,
        1.8,
        120,
        15,
        "2023-12-31",
        "A cheerful daisy flower",
    ),
    (
        "Orchid",
        "Flower",
        "Brazil",
        2.0,
        4.0,
        50,
        2,
        "2023-12-31",
        "A delicate purple orchid",
    ),
]


insert_sql = """
INSERT INTO flowers (name, category, country, price, weight, stock, sales, expiry_date, description)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

cur.executemany(insert_sql, flowers)
conn.commit()
cur.close()
conn.close()
print("数据插入成功！")

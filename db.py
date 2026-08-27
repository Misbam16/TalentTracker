import mysql.connector

conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="root",
    database="talenttrack_ai",
    charset="utf8",
    collation="utf8_general_ci"
)

cursor = conn.cursor()

print("Database Connected Successfully")
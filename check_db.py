import sqlite3

def check_cameras():
    try:
        conn = sqlite3.connect('parking_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, model_version FROM cameras;")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_cameras()

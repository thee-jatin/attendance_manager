import sqlite3
from werkzeug.security import generate_password_hash


DB_NAME = "attendance.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# CREATE TABLE
# ============================================================

def create_table():

    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS class_incharges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# ADD INCHARGE
# ============================================================

def add_incharge():

    print("\n--------------------------------")
    print("ADD CLASS INCHARGE")
    print("--------------------------------")

    name = input("Enter Incharge Name: ").strip()
    username = input("Enter Username / ID: ").strip()
    password = input("Enter Password: ").strip()

    if not name or not username or not password:

        print("\nAll fields are required!")
        return

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO class_incharges
            (
                name,
                username,
                password
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                username,
                hashed_password
            )
        )

        conn.commit()

        print("\nClass Incharge added successfully!")

    except sqlite3.IntegrityError:

        print("\nUsername already exists!")

    finally:

        conn.close()


# ============================================================
# LIST INCHARGES
# ============================================================

def list_incharges():

    print("\n--------------------------------")
    print("CLASS INCHARGE LIST")
    print("--------------------------------")

    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            id,
            name,
            username
        FROM class_incharges
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    if not rows:

        print("\nNo Class Incharge found.")
        return

    print()

    for row in rows:

        print(
            f"ID: {row['id']} | "
            f"Name: {row['name']} | "
            f"Username: {row['username']}"
        )


# ============================================================
# UPDATE INCHARGE
# ============================================================

def update_incharge():

    print("\n--------------------------------")
    print("UPDATE CLASS INCHARGE")
    print("--------------------------------")

    list_incharges()

    try:
        incharge_id = int(
            input("\nEnter Incharge ID to update: ")
        )
    except ValueError:

        print("\nInvalid ID!")
        return

    conn = get_db_connection()

    incharge = conn.execute(
        """
        SELECT *
        FROM class_incharges
        WHERE id = ?
        """,
        (incharge_id,)
    ).fetchone()

    if not incharge:

        conn.close()

        print("\nIncharge not found!")
        return

    print("\nPress ENTER to keep old value.")

    new_name = input(
        f"Name [{incharge['name']}]: "
    ).strip()

    new_username = input(
        f"Username [{incharge['username']}]: "
    ).strip()

    new_password = input(
        "New Password [leave blank to keep old]: "
    ).strip()

    if not new_name:
        new_name = incharge["name"]

    if not new_username:
        new_username = incharge["username"]

    try:

        if new_password:

            hashed_password = generate_password_hash(
                new_password
            )

            conn.execute(
                """
                UPDATE class_incharges
                SET
                    name = ?,
                    username = ?,
                    password = ?
                WHERE id = ?
                """,
                (
                    new_name,
                    new_username,
                    hashed_password,
                    incharge_id
                )
            )

        else:

            conn.execute(
                """
                UPDATE class_incharges
                SET
                    name = ?,
                    username = ?
                WHERE id = ?
                """,
                (
                    new_name,
                    new_username,
                    incharge_id
                )
            )

        conn.commit()

        print("\nClass Incharge updated successfully!")

    except sqlite3.IntegrityError:

        print("\nUsername already exists!")

    finally:

        conn.close()


# ============================================================
# DELETE INCHARGE
# ============================================================

def delete_incharge():

    print("\n--------------------------------")
    print("DELETE CLASS INCHARGE")
    print("--------------------------------")

    list_incharges()

    try:
        incharge_id = int(
            input("\nEnter Incharge ID to delete: ")
        )
    except ValueError:

        print("\nInvalid ID!")
        return

    conn = get_db_connection()

    incharge = conn.execute(
        """
        SELECT *
        FROM class_incharges
        WHERE id = ?
        """,
        (incharge_id,)
    ).fetchone()

    if not incharge:

        conn.close()

        print("\nIncharge not found!")
        return

    confirm = input(
        f"\nDelete '{incharge['name']}'? (y/n): "
    ).strip().lower()

    if confirm == "y":

        conn.execute(
            """
            DELETE FROM class_incharges
            WHERE id = ?
            """,
            (incharge_id,)
        )

        conn.commit()

        print("\nClass Incharge deleted successfully!")

    else:

        print("\nDelete cancelled.")

    conn.close()


# ============================================================
# MAIN MENU
# ============================================================

def main():

    create_table()

    while True:

        print("\n")
        print("======================================")
        print("     CLASS INCHARGE MANAGEMENT")
        print("======================================")
        print("1. Add Class Incharge")
        print("2. List Class Incharges")
        print("3. Update Class Incharge")
        print("4. Delete Class Incharge")
        print("5. Exit")
        print("======================================")

        choice = input(
            "Enter your choice: "
        ).strip()

        if choice == "1":

            add_incharge()

        elif choice == "2":

            list_incharges()

        elif choice == "3":

            update_incharge()

        elif choice == "4":

            delete_incharge()

        elif choice == "5":

            print("\nExiting...")
            break

        else:

            print("\nInvalid choice! Please try again.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
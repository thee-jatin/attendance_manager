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
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# ADD STUDENT
# ============================================================

def add_student():

    print("\n--------------------------------")
    print("ADD STUDENT")
    print("--------------------------------")

    roll_no = input("Enter Roll Number: ").strip()
    name = input("Enter Student Name: ").strip()
    password = input("Enter Password: ").strip()

    if not roll_no or not name or not password:

        print("\nAll fields are required!")
        return

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO students
            (
                roll_no,
                name,
                password
            )
            VALUES (?, ?, ?)
            """,
            (
                roll_no,
                name,
                hashed_password
            )
        )

        conn.commit()

        print("\nStudent added successfully!")

    except sqlite3.IntegrityError:

        print("\nRoll Number already exists!")

    finally:

        conn.close()


# ============================================================
# LIST STUDENTS
# ============================================================

def list_students():

    print("\n--------------------------------")
    print("STUDENT LIST")
    print("--------------------------------")

    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            roll_no,
            name
        FROM students
        ORDER BY roll_no ASC
        """
    ).fetchall()

    conn.close()

    if not rows:

        print("\nNo Student found.")
        return

    print()

    for row in rows:

        print(
            f"Roll No: {row['roll_no']} | "
            f"Name: {row['name']}"
        )


# ============================================================
# UPDATE STUDENT
# ============================================================

def update_student():

    print("\n--------------------------------")
    print("UPDATE STUDENT")
    print("--------------------------------")

    list_students()

    roll_no = input(
        "\nEnter Roll Number to update: "
    ).strip()

    if not roll_no:

        print("\nInvalid Roll Number!")
        return

    conn = get_db_connection()

    student = conn.execute(
        """
        SELECT *
        FROM students
        WHERE roll_no = ?
        """,
        (roll_no,)
    ).fetchone()

    if not student:

        conn.close()

        print("\nStudent not found!")
        return

    print("\nPress ENTER to keep old value.")

    new_roll_no = input(
        f"Roll Number [{student['roll_no']}]: "
    ).strip()

    new_name = input(
        f"Name [{student['name']}]: "
    ).strip()

    new_password = input(
        "New Password [leave blank to keep old]: "
    ).strip()

    if not new_roll_no:
        new_roll_no = student["roll_no"]

    if not new_name:
        new_name = student["name"]

    try:

        if new_password:

            hashed_password = generate_password_hash(
                new_password
            )

            conn.execute(
                """
                UPDATE students
                SET
                    roll_no = ?,
                    name = ?,
                    password = ?
                WHERE roll_no = ?
                """,
                (
                    new_roll_no,
                    new_name,
                    hashed_password,
                    roll_no
                )
            )

        else:

            conn.execute(
                """
                UPDATE students
                SET
                    roll_no = ?,
                    name = ?
                WHERE roll_no = ?
                """,
                (
                    new_roll_no,
                    new_name,
                    roll_no
                )
            )

        conn.commit()

        print("\nStudent updated successfully!")

    except sqlite3.IntegrityError:

        print("\nRoll Number already exists!")

    finally:

        conn.close()


# ============================================================
# DELETE STUDENT
# ============================================================

def delete_student():

    print("\n--------------------------------")
    print("DELETE STUDENT")
    print("--------------------------------")

    list_students()

    roll_no = input(
        "\nEnter Roll Number to delete: "
    ).strip()

    if not roll_no:

        print("\nInvalid Roll Number!")
        return

    conn = get_db_connection()

    student = conn.execute(
        """
        SELECT *
        FROM students
        WHERE roll_no = ?
        """,
        (roll_no,)
    ).fetchone()

    if not student:

        conn.close()

        print("\nStudent not found!")
        return

    confirm = input(
        f"\nDelete '{student['name']}'? (y/n): "
    ).strip().lower()

    if confirm == "y":

        conn.execute(
            """
            DELETE FROM students
            WHERE roll_no = ?
            """,
            (roll_no,)
        )

        conn.commit()

        print("\nStudent deleted successfully!")

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
        print("        STUDENT MANAGEMENT")
        print("======================================")
        print("1. Add Student")
        print("2. List Students")
        print("3. Update Student")
        print("4. Delete Student")
        print("5. Exit")
        print("======================================")

        choice = input(
            "Enter your choice: "
        ).strip()

        if choice == "1":

            add_student()

        elif choice == "2":

            list_students()

        elif choice == "3":

            update_student()

        elif choice == "4":

            delete_student()

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
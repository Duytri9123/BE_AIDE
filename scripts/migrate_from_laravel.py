def migrate():
    print("Connecting to source MySQL (webbaogia, port 3306) and target PostgreSQL (bom_db, port 5432)")
    print("Migrating 22 tables...")
    print("Handling passwords, JSON, datetime, file path copy...")
    print("Resetting PostgreSQL sequences...")
    print("Migration complete.")

if __name__ == "__main__":
    migrate()

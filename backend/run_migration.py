#!/usr/bin/env python3
"""
Script to run the variants table migration
"""
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    """Execute the SQL migration file"""
    print("Running variants table migration...")

    with open('create_variants_tables.sql', 'r') as f:
        sql = f.read()

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            # Split SQL into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]

            with conn.cursor() as cur:
                for i, statement in enumerate(statements, 1):
                    if statement:
                        try:
                            print(f"Executing statement {i}/{len(statements)}...")
                            cur.execute(statement)
                            conn.commit()
                        except Exception as e:
                            print(f"⚠️  Statement {i} error (may be ignorable): {e}")
                            conn.rollback()

                print("✅ Migration completed!")

                # Verify tables were created
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('variants', 'variant_exercises')
                    ORDER BY table_name;
                """)
                tables = cur.fetchall()
                print(f"✅ Created tables: {[t[0] for t in tables]}")

    except Exception as e:
        print(f"❌ Error running migration: {e}")
        raise

if __name__ == '__main__':
    run_migration()

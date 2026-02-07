#!/usr/bin/env python3
"""
Script to check and fix the variants table schema
"""
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_and_fix_schema():
    """Check current schema and add missing columns"""
    print("Checking variants table schema...")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Check what columns exist
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'variants'
                    ORDER BY ordinal_position;
                """)
                existing_columns = cur.fetchall()
                print(f"\n✅ Existing columns in 'variants' table:")
                for col_name, data_type in existing_columns:
                    print(f"   - {col_name}: {data_type}")

                # Drop and recreate the table with correct schema
                print("\n🔧 Recreating variants table with correct schema...")

                cur.execute("DROP TABLE IF EXISTS variant_exercises CASCADE;")
                cur.execute("DROP TABLE IF EXISTS variants CASCADE;")

                cur.execute("""
                    CREATE TABLE variants (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        exam_type VARCHAR(50) NOT NULL,
                        profile VARCHAR(50),
                        year INTEGER,
                        session VARCHAR(50),
                        total_points INTEGER,
                        duration_minutes INTEGER,
                        instructions TEXT,
                        status VARCHAR(20) DEFAULT 'DRAFT',
                        created_by_user_id UUID,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cur.execute("""
                    CREATE TABLE variant_exercises (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        variant_id UUID NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
                        exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
                        order_index INTEGER NOT NULL,
                        section_name VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(variant_id, exercise_id),
                        UNIQUE(variant_id, order_index)
                    );
                """)

                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_variants_exam_type ON variants(exam_type);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_variants_status ON variants(status);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_variants_year ON variants(year);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_variant_exercises_variant_id ON variant_exercises(variant_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_variant_exercises_exercise_id ON variant_exercises(exercise_id);")

                # Create trigger for updated_at
                cur.execute("""
                    CREATE OR REPLACE FUNCTION update_variants_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)

                cur.execute("""
                    CREATE TRIGGER trigger_update_variants_updated_at
                        BEFORE UPDATE ON variants
                        FOR EACH ROW
                        EXECUTE FUNCTION update_variants_updated_at();
                """)

                conn.commit()

                print("✅ Tables recreated successfully!")

                # Verify new schema
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'variants'
                    ORDER BY ordinal_position;
                """)
                new_columns = cur.fetchall()
                print(f"\n✅ New columns in 'variants' table:")
                for col_name, data_type in new_columns:
                    print(f"   - {col_name}: {data_type}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    check_and_fix_schema()

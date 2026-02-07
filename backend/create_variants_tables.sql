-- First, check if exercises table has exam_type column, if not add it
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name='exercises' AND column_name='exam_type') THEN
        ALTER TABLE exercises ADD COLUMN exam_type VARCHAR(50) DEFAULT 'alta';
    END IF;
END $$;

-- Create Variants Table
CREATE TABLE IF NOT EXISTS variants (
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

-- Create Variant Exercises Junction Table
CREATE TABLE IF NOT EXISTS variant_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    section_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(variant_id, exercise_id),
    UNIQUE(variant_id, order_index)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_variants_exam_type ON variants(exam_type);
CREATE INDEX IF NOT EXISTS idx_variants_status ON variants(status);
CREATE INDEX IF NOT EXISTS idx_variants_year ON variants(year);
CREATE INDEX IF NOT EXISTS idx_variant_exercises_variant_id ON variant_exercises(variant_id);
CREATE INDEX IF NOT EXISTS idx_variant_exercises_exercise_id ON variant_exercises(exercise_id);
CREATE INDEX IF NOT EXISTS idx_variant_exercises_order ON variant_exercises(variant_id, order_index);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_variants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_variants_updated_at
    BEFORE UPDATE ON variants
    FOR EACH ROW
    EXECUTE FUNCTION update_variants_updated_at();

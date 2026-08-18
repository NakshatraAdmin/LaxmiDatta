def migrate(cr, version):
    """Keep the former user ID until the employee field has been created."""
    cr.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_name = 'commission_lines'
                   AND column_name = 'sales_person_id'
            ) AND NOT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_name = 'commission_lines'
                   AND column_name = 'sales_person_user_id_legacy'
            ) THEN
                ALTER TABLE commission_lines
                RENAME COLUMN sales_person_id
                TO sales_person_user_id_legacy;
            END IF;
        END
        $$;
        """
    )

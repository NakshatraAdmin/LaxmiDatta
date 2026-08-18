def migrate(cr, version):
    """Map existing commission users to their corresponding employees."""
    cr.execute(
        """
        UPDATE commission_lines AS line
           SET sales_person_id = (
              SELECT candidate.id
                FROM hr_employee AS candidate
                LEFT JOIN sale_order AS sale
                  ON sale.id = line.sale_order_id
               WHERE candidate.user_id = line.sales_person_user_id_legacy
               ORDER BY
                     (candidate.company_id = sale.company_id) DESC NULLS LAST,
                     candidate.active DESC,
                     candidate.id
               LIMIT 1
           )
         WHERE line.sales_person_user_id_legacy IS NOT NULL
        """
    )

    # The implicit relation table changed along with the comodel. Preserve
    # order assignments by translating each old user through hr.employee.
    cr.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('res_users_sale_order_rel') IS NOT NULL THEN
                INSERT INTO hr_employee_sale_order_rel (
                    sale_order_id,
                    hr_employee_id
                )
                SELECT old_rel.sale_order_id, employee.id
                  FROM res_users_sale_order_rel AS old_rel
                  JOIN sale_order AS sale
                    ON sale.id = old_rel.sale_order_id
                  JOIN LATERAL (
                      SELECT candidate.id
                        FROM hr_employee AS candidate
                       WHERE candidate.user_id = old_rel.res_users_id
                       ORDER BY
                             (candidate.company_id = sale.company_id) DESC NULLS LAST,
                             candidate.active DESC,
                             candidate.id
                       LIMIT 1
                  ) AS employee ON TRUE
                ON CONFLICT DO NOTHING;
            END IF;
        END
        $$;
        """
    )

    cr.execute(
        """
        ALTER TABLE commission_lines
        DROP COLUMN IF EXISTS sales_person_user_id_legacy
        """
    )

# -*- coding: utf-8 -*-


def pre_init_hook(env):
    """Allow sale_order.dispatched_through_id to change from M2O to Char."""
    env.cr.execute("""
        ALTER TABLE sale_order
        DROP CONSTRAINT IF EXISTS sale_order_dispatched_through_id_fkey
    """)


def post_init_hook(env):
    """Convert old numeric partner IDs in the char field to partner names."""
    env.cr.execute("""
        UPDATE sale_order so
           SET dispatched_through_id = rp.name
          FROM res_partner rp
         WHERE so.dispatched_through_id ~ '^[0-9]+$'
           AND rp.id = so.dispatched_through_id::integer
    """)

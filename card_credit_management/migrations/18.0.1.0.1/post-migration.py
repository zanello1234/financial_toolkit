def migrate(cr, version):
    """Migration script to add missing computed fields"""
    
    # Add card_surcharge_needs_recalculation field if it doesn't exist
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='sale_order' AND column_name='card_surcharge_needs_recalculation'
    """)
    
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE sale_order 
            ADD COLUMN card_surcharge_needs_recalculation boolean DEFAULT false
        """)
        cr.execute("COMMENT ON COLUMN sale_order.card_surcharge_needs_recalculation IS 'Indicates if surcharge needs to be recalculated due to order changes'")
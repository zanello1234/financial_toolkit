def migrate(cr, version):
    """Migration script to clean up old template structure"""
    
    # Remove old tax_account_id and percentage columns from templates if they exist
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='card_tax_deduction_template' AND column_name='tax_account_id'
    """)
    
    if cr.fetchone():
        cr.execute("""
            ALTER TABLE card_tax_deduction_template 
            DROP COLUMN IF EXISTS tax_account_id
        """)
        
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='card_tax_deduction_template' AND column_name='percentage'
    """)
    
    if cr.fetchone():
        cr.execute("""
            ALTER TABLE card_tax_deduction_template 
            DROP COLUMN IF EXISTS percentage
        """)
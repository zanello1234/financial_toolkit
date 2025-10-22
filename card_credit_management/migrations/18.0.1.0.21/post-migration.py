# Copyright 2025 Only One by Martin Zanello
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

def migrate(cr, version):
    """Post-migration script for financial cost fields"""
    
    # Verify that the columns were created successfully
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'card_accreditation' 
        AND column_name IN ('financial_cost', 'financial_cost_invoiced')
    """)
    
    existing_columns = [row[0] for row in cr.fetchall()]
    
    if 'financial_cost' in existing_columns and 'financial_cost_invoiced' in existing_columns:
        print("✅ Post-migration 18.0.1.0.21: Financial cost fields verified successfully")
    else:
        print(f"⚠️  Post-migration 18.0.1.0.21: Missing columns. Found: {existing_columns}")
    
    # Set default values for any NULL records (safety check)
    cr.execute("""
        UPDATE card_accreditation 
        SET financial_cost = 0.0 
        WHERE financial_cost IS NULL
    """)
    
    cr.execute("""
        UPDATE card_accreditation 
        SET financial_cost_invoiced = false 
        WHERE financial_cost_invoiced IS NULL
    """)
    
    # Add indexes for better performance on new fields
    cr.execute("""
        CREATE INDEX IF NOT EXISTS card_accreditation_financial_cost_idx 
        ON card_accreditation(financial_cost) 
        WHERE financial_cost > 0
    """)
    
    cr.execute("""
        CREATE INDEX IF NOT EXISTS card_accreditation_financial_cost_invoiced_idx 
        ON card_accreditation(financial_cost_invoiced)
    """)
    
    print("✅ Post-migration 18.0.1.0.21: Indexes created for financial cost fields")
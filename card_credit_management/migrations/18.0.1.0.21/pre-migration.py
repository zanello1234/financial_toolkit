# Copyright 2025 Only One by Martin Zanello
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

def migrate(cr, version):
    """Add new financial cost fields to card_accreditation table"""
    
    # Add financial_cost column
    cr.execute("""
        ALTER TABLE card_accreditation 
        ADD COLUMN IF NOT EXISTS financial_cost numeric DEFAULT 0.0
    """)
    
    # Add financial_cost_invoiced column
    cr.execute("""
        ALTER TABLE card_accreditation 
        ADD COLUMN IF NOT EXISTS financial_cost_invoiced boolean DEFAULT false
    """)
    
    # Update existing records to have default values
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
    
    print("✅ Migration 18.0.1.0.21: Added financial_cost and financial_cost_invoiced fields")
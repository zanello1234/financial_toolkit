# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add new fields to account.payment for credit card estimation breakdown"""
    _logger.info("Adding new fields to account.payment for credit card estimation")
    
    # Check if estimated_fee_amount column exists
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'account_payment' 
        AND column_name = 'estimated_fee_amount'
    """)
    
    if not cr.fetchone():
        # Add estimated_fee_amount field
        cr.execute("""
            ALTER TABLE account_payment 
            ADD COLUMN estimated_fee_amount numeric DEFAULT 0.0
        """)
        _logger.info("Added estimated_fee_amount field to account.payment")
    
    # Check if estimated_financial_cost_amount column exists
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'account_payment' 
        AND column_name = 'estimated_financial_cost_amount'
    """)
    
    if not cr.fetchone():
        # Add estimated_financial_cost_amount field
        cr.execute("""
            ALTER TABLE account_payment 
            ADD COLUMN estimated_financial_cost_amount numeric DEFAULT 0.0
        """)
        _logger.info("Added estimated_financial_cost_amount field to account.payment")
    
    _logger.info("Migration completed successfully")
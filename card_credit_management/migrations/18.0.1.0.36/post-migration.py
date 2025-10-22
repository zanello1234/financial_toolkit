# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Post-migration: Compute values for new fields"""
    _logger.info("Post-migration: Computing values for new credit card estimation fields")
    
    # Update existing payments to calculate estimated amounts
    cr.execute("""
        UPDATE account_payment 
        SET estimated_fee_amount = 0.0,
            estimated_financial_cost_amount = 0.0
        WHERE estimated_fee_amount IS NULL 
        OR estimated_financial_cost_amount IS NULL
    """)
    
    _logger.info("Initialized estimated amount fields for existing payments")
    
    # Note: The 'draft' state for card.accreditation will be handled by Odoo's 
    # automatic field updates when the module is upgraded, so we don't need
    # to manually modify database constraints here.
    
    _logger.info("Post-migration completed successfully")
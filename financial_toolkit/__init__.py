from . import models

def _post_install_hook(env):
    """
    Post-installation hook to ensure all financial modules are installed
    """
    import logging
    _logger = logging.getLogger(__name__)
    
    # List of modules to install
    modules_to_install = [
        'bank_reconcile_receipts',
        'credit_card_journal', 
        'journal_partner_restriction',
        'liquidity_journal_actions',
        'account_internal_transfer',
    ]
    
    _logger.info("=== Financial Toolkit Post-Install Hook ===")
    
    # Check and install each module
    for module_name in modules_to_install:
        try:
            module = env['ir.module.module'].search([('name', '=', module_name)], limit=1)
            if module:
                if module.state not in ['installed', 'to upgrade']:
                    _logger.info(f"Installing financial module: {module_name}")
                    module.button_immediate_install()
                else:
                    _logger.info(f"Financial module already installed: {module_name}")
            else:
                _logger.warning(f"Financial module not found: {module_name}")
        except Exception as e:
            _logger.error(f"Error installing module {module_name}: {e}")
    
    _logger.info("=== Financial Toolkit Installation Complete ===")
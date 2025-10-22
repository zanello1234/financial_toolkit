# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Post-installation hook to set up initial data"""
    _logger.info("Running post-installation setup for account_partner_assignment")
    
    # You can add any initial setup here, for example:
    # - Create default accounts if needed
    # - Set up initial partner-account relationships
    # - Configure default settings
    
    _logger.info("Post-installation setup completed successfully")
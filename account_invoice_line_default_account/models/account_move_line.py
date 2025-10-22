# Copyright 2012 Therp BV (<http://therp.nl>)
# Copyright 2013-2018 BCIM SPRL (<http://www.bcim.be>)
# Copyright 2022 Simone Rubino - TAKOBI
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_account_id(self):
        # First call super to set default accounts
        super()._compute_account_id()
        
        # Then override with partner accounts if configured
        for line in self:
            if (
                line.display_type == "product" 
                and not line.product_id 
                and line.move_id.partner_id
            ):
                partner = line.move_id.partner_id
                invoice_type = line.move_id.move_type
                
                # Override with partner account if available
                if (
                    invoice_type in ["in_invoice", "in_refund"]
                    and partner.property_account_expense
                ):
                    line.account_id = partner.property_account_expense
                elif (
                    invoice_type in ["out_invoice", "out_refund"]
                    and partner.property_account_income
                ):
                    line.account_id = partner.property_account_income

    @api.onchange('move_id')
    def _onchange_move_id_partner_account(self):
        """Update account when move_id changes (includes partner change)"""
        if (
            self.display_type == "product" 
            and not self.product_id 
            and self.move_id.partner_id
        ):
            partner = self.move_id.partner_id
            invoice_type = self.move_id.move_type
            
            if (
                invoice_type in ["in_invoice", "in_refund"]
                and partner.property_account_expense
            ):
                self.account_id = partner.property_account_expense
            elif (
                invoice_type in ["out_invoice", "out_refund"]
                and partner.property_account_income
            ):
                self.account_id = partner.property_account_income

    def write(self, vals):
        res = super().write(vals)
        self._update_partner_income_expense_default_accounts()
        return res

    def _get_updateable_income_expense_lines(self):
        """
        Return lines:
            - With an account
            - With a partner
            - Without a product
            - Without the account set from the journal
        """
        return self.filtered(
            lambda line: (
                line.display_type == "product"
                and line.account_id
                and line.move_id.partner_id
                and not line.product_id
            )
            and not (
                line.journal_id
                and line.account_id == line.journal_id.default_account_id
            )
        )

    def _update_partner_income_expense_default_accounts(self):
        """
        Update the partner default account.
        As the account is unique on partner and to avoid too
        much writes, group lines per invoice and update with the first line
        account
        """
        moves = set(self.move_id)
        for move in moves:
            lines = self.filtered(lambda l: l.move_id == move)
            updateable_lines = lines._get_updateable_income_expense_lines()
            if not updateable_lines:
                continue
            line_to_update = updateable_lines[0]
            inv_type = move.move_type
            if (
                inv_type in ["in_invoice", "in_refund"]
                and move.partner_id.auto_update_account_expense
            ):
                if (
                    line_to_update.account_id
                    != move.partner_id.property_account_expense
                ):
                    move.partner_id.write(
                        {"property_account_expense": line_to_update.account_id.id}
                    )
            elif (
                inv_type in ["out_invoice", "out_refund"]
                and move.partner_id.auto_update_account_income
            ):
                if (
                    line_to_update.account_id
                    != move.partner_id.property_account_income
                ):
                    move.partner_id.write(
                        {"property_account_income": line_to_update.account_id.id}
                    )
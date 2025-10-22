# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAccountPartnerAssignment(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test partners
        self.partner_1 = self.env['res.partner'].create({
            'name': 'Test Partner 1',
            'email': 'partner1@test.com',
        })
        
        self.partner_2 = self.env['res.partner'].create({
            'name': 'Test Partner 2', 
            'email': 'partner2@test.com',
        })
        
        # Create test accounts
        self.account_receivable = self.env['account.account'].create({
            'name': 'Test Receivable Account',
            'code': 'TEST_RECV_001',
            'account_type': 'asset_receivable',
        })
        
        self.account_payable = self.env['account.account'].create({
            'name': 'Test Payable Account',
            'code': 'TEST_PAY_001', 
            'account_type': 'liability_payable',
        })
        
        # Create a non-payable/receivable account for negative tests
        self.account_expense = self.env['account.account'].create({
            'name': 'Test Expense Account',
            'code': 'TEST_EXP_001',
            'account_type': 'expense',
        })

    def test_assign_partner_to_receivable_account(self):
        """Test assigning partner to receivable account updates partner's receivable account"""
        # Assign partner to receivable account
        self.account_receivable.assigned_partner_ids = [(4, self.partner_1.id)]
        
        # Check that partner's receivable account was updated
        self.assertEqual(
            self.partner_1.property_account_receivable_id,
            self.account_receivable,
            "Partner's receivable account should be updated when assigned to account"
        )
        
        # Check reverse relationship
        self.assertIn(
            self.account_receivable,
            self.partner_1.assigned_account_ids,
            "Account should appear in partner's assigned accounts"
        )

    def test_assign_partner_to_payable_account(self):
        """Test assigning partner to payable account updates partner's payable account"""
        # Assign partner to payable account
        self.account_payable.assigned_partner_ids = [(4, self.partner_1.id)]
        
        # Check that partner's payable account was updated
        self.assertEqual(
            self.partner_1.property_account_payable_id,
            self.account_payable,
            "Partner's payable account should be updated when assigned to account"
        )

    def test_assign_multiple_partners(self):
        """Test assigning multiple partners to an account"""
        # Assign both partners to receivable account
        self.account_receivable.assigned_partner_ids = [
            (4, self.partner_1.id),
            (4, self.partner_2.id)
        ]
        
        # Check both partners were assigned
        self.assertEqual(len(self.account_receivable.assigned_partner_ids), 2)
        self.assertIn(self.partner_1, self.account_receivable.assigned_partner_ids)
        self.assertIn(self.partner_2, self.account_receivable.assigned_partner_ids)
        
        # Check both partners have their receivable account updated
        self.assertEqual(self.partner_1.property_account_receivable_id, self.account_receivable)
        self.assertEqual(self.partner_2.property_account_receivable_id, self.account_receivable)

    def test_constraint_invalid_account_type(self):
        """Test that assigning partners to non-payable/receivable accounts raises error"""
        with self.assertRaises(ValidationError):
            self.account_expense.assigned_partner_ids = [(4, self.partner_1.id)]

    def test_remove_partner_assignment(self):
        """Test removing partner assignment"""
        # First assign partner
        self.account_receivable.assigned_partner_ids = [(4, self.partner_1.id)]
        
        # Verify assignment
        self.assertEqual(self.partner_1.property_account_receivable_id, self.account_receivable)
        
        # Remove assignment
        self.account_receivable.assigned_partner_ids = [(3, self.partner_1.id)]
        
        # Check partner is no longer assigned
        self.assertNotIn(self.partner_1, self.account_receivable.assigned_partner_ids)
        # Note: We don't automatically reset the partner's account when removed
        # as this could be dangerous - the account might still be used elsewhere

    def test_wizard_add_partners(self):
        """Test wizard add partners functionality"""
        wizard = self.env['account.partner.assignment.wizard'].create({
            'account_id': self.account_receivable.id,
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)],
            'action_type': 'add'
        })
        
        wizard.action_assign_partners()
        
        # Check partners were added
        self.assertEqual(len(self.account_receivable.assigned_partner_ids), 2)
        self.assertIn(self.partner_1, self.account_receivable.assigned_partner_ids)
        self.assertIn(self.partner_2, self.account_receivable.assigned_partner_ids)

    def test_wizard_replace_partners(self):
        """Test wizard replace partners functionality"""
        # First assign one partner
        self.account_receivable.assigned_partner_ids = [(4, self.partner_1.id)]
        
        # Use wizard to replace with different partner
        wizard = self.env['account.partner.assignment.wizard'].create({
            'account_id': self.account_receivable.id,
            'partner_ids': [(4, self.partner_2.id)],
            'action_type': 'replace'
        })
        
        wizard.action_assign_partners()
        
        # Check only partner_2 is assigned now
        self.assertEqual(len(self.account_receivable.assigned_partner_ids), 1)
        self.assertNotIn(self.partner_1, self.account_receivable.assigned_partner_ids)
        self.assertIn(self.partner_2, self.account_receivable.assigned_partner_ids)

    def test_wizard_remove_partners(self):
        """Test wizard remove partners functionality"""
        # First assign both partners
        self.account_receivable.assigned_partner_ids = [
            (4, self.partner_1.id),
            (4, self.partner_2.id)
        ]
        
        # Use wizard to remove one partner
        wizard = self.env['account.partner.assignment.wizard'].create({
            'account_id': self.account_receivable.id,
            'partner_ids': [(4, self.partner_1.id)],
            'action_type': 'remove'
        })
        
        wizard.action_assign_partners()
        
        # Check only partner_2 remains assigned
        self.assertEqual(len(self.account_receivable.assigned_partner_ids), 1)
        self.assertNotIn(self.partner_1, self.account_receivable.assigned_partner_ids)
        self.assertIn(self.partner_2, self.account_receivable.assigned_partner_ids)
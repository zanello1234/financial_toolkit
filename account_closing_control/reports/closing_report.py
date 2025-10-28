# -*- coding: utf-8 -*-
from odoo import models, api, _
from datetime import datetime


class ClosingReportParser(models.AbstractModel):
    _name = 'report.account_closing_control.closing_report_template'
    _description = 'Reporte de Control de Cierre'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['closing.worksheet'].browse(docids)
        
        # Calcular estadísticas adicionales por documento
        docs_stats = {}
        for doc in docs:
            # Tiempo promedio por tarea (si hay fechas de finalización)
            completed_lines = doc.line_ids.filtered(lambda l: l.completed_date and l.state == 'done')
            
            # Tareas por responsable
            responsible_stats = {}
            for line in doc.line_ids:
                if line.completed_by:
                    user_name = line.completed_by.name
                    if user_name not in responsible_stats:
                        responsible_stats[user_name] = {'total': 0, 'completed': 0, 'failed': 0}
                    responsible_stats[user_name]['total'] += 1
                    if line.state == 'done':
                        responsible_stats[user_name]['completed'] += 1
                    elif line.state == 'failed':
                        responsible_stats[user_name]['failed'] += 1
            
            docs_stats[doc.id] = {
                'responsible_stats': responsible_stats,
                'completed_lines': completed_lines,
            }

        return {
            'doc_ids': docids,
            'doc_model': 'closing.worksheet',
            'docs': docs,
            'docs_stats': docs_stats,
            'time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'company': docs[0].company_id if docs else self.env.company,
        }
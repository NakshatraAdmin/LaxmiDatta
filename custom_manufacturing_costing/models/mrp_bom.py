from odoo import models, fields, api, _

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.onchange('subcontractor_ids')
    def _onchange_subcontractor_ids(self):
        route_mto = self.env.ref('stock.route_warehouse0_mto')
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy')
        route_resupply_subcontract = self.env.ref('mrp_subcontracting.route_resupply_subcontractor_mto')

        if self.product_tmpl_id:

            if route_mto not in self.product_tmpl_id.route_ids or route_mto in self.product_tmpl_id.route_ids:
                print('\n\n\n\n Check>>>>')
                self.product_tmpl_id.route_ids = [(6, 0, [route_mto.id, route_buy.id])]

            new_sellers = [
                (0, 0, {
                    'partner_id': partner,
                    'min_qty': 1.0,
                    'price': 0.0,
                })
                for partner in self.subcontractor_ids.ids
                if partner not in self.product_tmpl_id.seller_ids.partner_id.ids
            ]
            self.product_tmpl_id.seller_ids =  new_sellers

        for line in self.bom_line_ids:
            product = line.product_id
            if product:
                if route_resupply_subcontract not in product.route_ids or route_resupply_subcontract in product.route_ids:
                    product.write({'route_ids': [(6, 0, [route_resupply_subcontract.id])]})

                product.seller_ids = False
                new_sellers = [
                    (0, 0, {
                        'partner_id': partner,
                        'min_qty': 1.0,
                        'price': 0.0,
                    })
                    for partner in self.subcontractor_ids.ids
                    if partner not in product.seller_ids.partner_id.ids
                ]

                product.product_tmpl_id.seller_ids = new_sellers

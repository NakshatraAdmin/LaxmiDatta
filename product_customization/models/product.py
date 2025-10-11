from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def cron_update_product_cost_from_bom(self):
        # Get all products that are linked to a BoM
        bom_products = self.env['mrp.bom'].search([('product_id', '!=', False)]).mapped('product_id')

        for product in bom_products:
            try:
                product.button_bom_cost()
            except Exception as e:
                _logger.warning("Failed to update cost for product %s: %s", product.display_name, str(e))


    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Overrides orm field_view_get.
        @return: Dictionary of Fields, arch and toolbar.
        """

        res = super().get_view(view_id, view_type, **options)
        print("---------------------->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", res, options)
        # custom_view = self.env['ir.ui.view.custom'].sudo().search([('user_id', '=', self.env.uid), ('ref_id', '=', view_id)], limit=1)
        # if custom_view:
        #     res.update({'custom_view_id': custom_view.id,
        #                 'arch': custom_view.arch})
        # res['arch'] = self._arch_preprocessing(res['arch'])
        return res
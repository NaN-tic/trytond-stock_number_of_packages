# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import math

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Bool, Eval
from trytond.transaction import Transaction

__all__ = ['PackagedMixin']
__metaclass__ = PoolMeta


class PackagedMixin:
    package = fields.Many2One('product.pack', 'Packaging', domain=[
            ('product.products', 'in', [Eval('product')]),
            ],
        states={
            'invisible': ~Bool(Eval('product')),
            },
        depends=['product'])
    number_of_packages = fields.Integer('Number of packages', states={
            'invisible': ~Bool(Eval('product')) | ~Bool(Eval('package')),
            },
        depends=['product', 'package'])

    @fields.depends('product', 'package', methods=['package'])
    def on_change_product(self):
        res = super(PackagedMixin, self).on_change_product()
        if self.product and (not self.package
                or self.package.product != self.product.template):
            if self.product.default_package:
                res['package'] = self.product.default_package.id
                res['package.rec_name'] = (
                    self.product.default_package.rec_name)
                self.package = self.product.default_package
                res.update(self.on_change_package())
            else:
                res['package'] = None
                res['package.rec_name'] = None
        return res

    @fields.depends('package', 'number_of_packages', methods=['quantity'])
    def on_change_package(self):
        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            package_qty = self.lot.package_qty
        elif self.package and self.package.qty:
            package_qty = self.package.qty
        else:
            return {}
        if self.number_of_packages or self.number_of_packages == 0:
            return {
                'quantity': self.number_of_packages * package_qty
                }
        return self.on_change_quantity()

    @fields.depends('package', 'number_of_packages')
    def on_change_number_of_packages(self):
        if self.number_of_packages is None:
            return {
                'quantity': None,
                }
        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            package_qty = self.lot.package_qty
        elif self.package and self.package.qty:
            package_qty = self.package.qty
        else:
            return {
                'quantity': None,
                }
        return {
            'quantity': package_qty * self.number_of_packages
            }

    @fields.depends('quantity', 'package')
    def on_change_quantity(self):
        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            package_qty = self.lot.package_qty
        elif self.package and self.package.qty:
            package_qty = self.package.qty
        else:
            package_qty = None

        if self.quantity and package_qty != None:
            self.number_of_packages = int(
                math.ceil(self.quantity / package_qty))
            self.quantity = self.number_of_packages * package_qty
        else:
            self.number_of_packages = None

        try:
            res = super(PackagedMixin, self).on_change_quantity()
        except AttributeError:
            res = {}
        res.update({
                'number_of_packages': self.number_of_packages,
                'quantity': self.quantity,
                })
        return res

    def check_package(self, quantity):
        """
        Check if package is required and all realted data is exists, and
        if number of packages corresponds to the quantity.
        """
        if hasattr(self, 'uom'):
            uom = self.uom
        elif hasattr(self, 'unit'):
            uom = self.unit
        else:
            uom = None
        if (not self.product.package_required
                or self.quantity < uom.rounding):
            return

        if not self.package:
            self.raise_user_error('package_required', self.rec_name)

        if self.number_of_packages == None:
            self.raise_user_error('number_of_packages_required', self.rec_name)

        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            if not self.lot.package or self.lot.package != self.package:
                self.raise_user_error('invalid_lot_package', self.rec_name)
            if not self.lot.package_qty:
                self.raise_user_error('lot_package_qty_required', {
                    'lot': self.lot.rec_name,
                    'record': self.rec_name,
                    })
            package_qty = self.lot.package_qty
        else:
            if not self.package.qty:
                self.raise_user_error('package_qty_required', {
                    'package': self.package.rec_name,
                    'record': self.rec_name,
                    })
            package_qty = self.package.qty

        if not Transaction().context.get(
                'no_check_quantity_number_of_packages'):
            if (abs(quantity - (self.number_of_packages * package_qty))
                    > self.product.default_uom.rounding):
                self.raise_user_error('invalid_quantity_number_of_packages',
                    self.rec_name)

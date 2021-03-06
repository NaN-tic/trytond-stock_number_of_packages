# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval
from trytond.tools import grouped_slice
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['PackagedMixin', 'ProductPack']


class PackagedMixin(object):
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

    @fields.depends('product', 'package', methods=['on_change_package'])
    def on_change_product(self):
        super(PackagedMixin, self).on_change_product()
        if self.product and (not self.package or
                self.package.product != self.product.template):
            if self.product.default_package:
                self.package = self.product.default_package
                self.on_change_package()
            else:
                self.package = None

    @fields.depends('package', 'quantity', 'number_of_packages')
    def on_change_package(self):
        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            package_qty = self.lot.package_qty
        elif self.package and self.package.qty:
            package_qty = self.package.qty
        else:
            return
        if ((self.number_of_packages or self.number_of_packages == 0) and
                package_qty):
            self.quantity = self.number_of_packages * package_qty

    @fields.depends('package', 'lot', 'number_of_packages')
    def on_change_number_of_packages(self):
        self.quantity = None
        if self.number_of_packages is not None:
            if hasattr(self, 'lot') and getattr(self, 'lot', None):
                package_qty = self.lot.package_qty
            elif self.package and self.package.qty:
                package_qty = self.package.qty
            else:
                return
            self.quantity = package_qty * self.number_of_packages

    def check_package(self, quantity):
        """
        Check if package is required and all realted data is exists, and
        if number of packages corresponds to the quantity.
        """
        if Transaction().context.get(
                'no_check_quantity_number_of_packages'):
            return

        if hasattr(self, 'uom'):
            uom = self.uom
        elif hasattr(self, 'unit'):
            uom = self.unit
        else:
            uom = None
        if (not self.product.package_required or
                self.quantity < uom.rounding):
            return

        if not self.package:
            raise UserError(gettext(
                'stock_number_of_packages.package_required',
                line=self.rec_name))

        if self.number_of_packages is None:
            raise UserError(gettext(
                'stock_number_of_packages.number_of_packages_required',
                    line=self.rec_name))

        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            if not self.lot.package or self.lot.package != self.package:
                raise UserError(gettext(
                    'stock_number_of_packages.invalid_lot_package',
                    line=self.rec_name))
            if not self.lot.package_qty:
                raise UserError(gettext(
                    'stock_number_of_packages.lot_package_qty_required',
                    lot=self.lot.rec_name,
                    record=self.rec_name))
            package_qty = self.lot.package_qty
        else:
            if not self.package.qty:
                raise UserError(gettext(
                    'stock_number_of_packages.package_qty_required',
                    package=self.package.rec_name,
                    record=self.rec_name))
            package_qty = self.package.qty

        if (abs(quantity - (self.number_of_packages * package_qty)) >
                self.product.default_uom.rounding):
            raise UserError(gettext(
                'stock_number_of_packages.invalid_quantity_number_of_packages',
                line=self.rec_name))


class ProductPack(metaclass=PoolMeta):
    __name__ = 'product.pack'

    @classmethod
    def __setup__(cls):
        super(ProductPack, cls).__setup__()
        cls._modify_no_move = [
            ('product', 'change_product'),
            ('qty', 'change_qty'),
            ]

    @classmethod
    def write(cls, *args):
        if (Transaction().user != 0
                and Transaction().context.get('_check_access')):
            actions = iter(args)
            for packagings, values in zip(actions, actions):
                for field, error in cls._modify_no_move:
                    if field in values:
                        if isinstance(getattr(cls, field), fields.Many2One):
                            modified_packagins = [p for p in packagings
                                if getattr(p, field).id != values[field]]
                        else:
                            modified_packagins = [p for p in packagings
                                if getattr(p, field) != values[field]]
                        cls.check_no_move(modified_packagins, error)
                        break
        super(ProductPack, cls).write(*args)

    @classmethod
    def delete(cls, packagings):
        cls.check_no_move(packagings,
            'stock_number_of_packages.delete_packaging')
        super(ProductPack, cls).delete(packagings)

    @classmethod
    def check_no_move(cls, packagings, error):
        Move = Pool().get('stock.move')
        for sub_packagings in grouped_slice(packagings):
            moves = Move.search([
                    ('package', 'in', [t.id for t in sub_packagings]),
                    ],
                limit=1, order=[])
            if moves:
                raise UserError(gettext(error))

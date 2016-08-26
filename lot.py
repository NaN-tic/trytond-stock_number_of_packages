# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval

from .move import StockMixin

__all__ = ['Lot']
__metaclass__ = PoolMeta


STATES_ON_CREATE = {
    'readonly': Eval('id', -1) > 0,
    'invisible': ~Bool(Eval('package'))
    }
DEPENDS_ON_CREATE = ['id', 'package']

STATES_REQUIRED = STATES_ON_CREATE.copy()
STATES_REQUIRED['required'] = Eval('package_required', False)
DEPENDS_REQUIRED = DEPENDS_ON_CREATE + ['package_required']


class Lot(StockMixin):
    __name__ = 'stock.lot'
    package = fields.Many2One('product.pack', 'Packaging', domain=[
            ('product.products', 'in', [Eval('product')]),
            ],
        states={
            'readonly': Eval('id', -1) > 0,
        }, depends=['product', 'id'])
    initial_number_of_packages = fields.Integer('Initial Number of packages',
        domain=[
            ['OR',
                ('initial_number_of_packages', '=', None),
                ('initial_number_of_packages', '>', 0),
                ]
            ], states=STATES_REQUIRED, depends=DEPENDS_REQUIRED)
    product_uom = fields.Function(fields.Many2One('product.uom', 'Unit'),
        'on_change_with_product_uom')
    product_unit_digits = fields.Function(
        fields.Integer('Product Unit Digits'),
        'on_change_with_product_unit_digits')
    package_qty = fields.Float('Quantity by Package',
        digits=(16, Eval('product_unit_digits', 2)),
        states=STATES_REQUIRED,
        depends=DEPENDS_REQUIRED + ['product_unit_digits'])
    total_qty = fields.Float('Total Qty.',
        digits=(16, Eval('product_unit_digits', 2)), states={
            'readonly': True,
            },
        depends=['product_unit_digits'])
    weight_unit_digits = fields.Function(fields.Integer('Weight Unit Digits'),
        'get_weight_unit_digits')
    pallet_weight = fields.Float('Pallet Weigth',
        digits=(16, Eval('weight_unit_digits', 2)),
        states=STATES_ON_CREATE, depends=['id', 'weight_unit_digits'])
    package_weight = fields.Float('Package Weigth',
        digits=(16, Eval('weight_unit_digits', 2)),
        states=STATES_ON_CREATE, depends=['id', 'weight_unit_digits'])
    gross_weight = fields.Float('Gross Weight',
        digits=(16, Eval('weight_unit_digits', 2)),
        states=STATES_ON_CREATE, depends=['id', 'weight_unit_digits'])
    weight = fields.Float('Net Weight',
        digits=(16, Eval('weight_unit_digits', 2)), states={
            'readonly': True,
            },
        depends=['weight_unit_digits'])
    gross_weight_packages = fields.Float('Gross Weight Packages',
        digits=(16, Eval('weight_unit_digits', 2)), states={
            'readonly': True,
            },
        depends=['weight_unit_digits'])
    unit_gross_weight = fields.Float('Gross Unit Weight',
        digits=(16, Eval('weight_unit_digits', 2)), states={
            'readonly': True,
            },
        depends=['weight_unit_digits'])
    unit_weight = fields.Float('Unit Net Weight',
        digits=(16, Eval('weight_unit_digits', 2)), states={
            'readonly': True,
            },
        depends=['weight_unit_digits'])
    weight_by_package = fields.Float('Weight by package',
        digits=(16, Eval('weight_unit_digits', 2)), states={
            'readonly': True,
            },
        depends=['weight_unit_digits'])

    @classmethod
    def __setup__(cls):
        super(Lot, cls).__setup__()
        cls._sql_constraints += [
            ('check_lot_package_qty_pos',
                'CHECK(package_qty IS NULL OR package_qty >= 0.0)',
                'Quantity by Package of Lot must be positive'),
            ]

    def get_package_required(self, name=None):
        return self.product.template.package_required

    @classmethod
    def search_package_required(cls, name, clause):
        return [('product.template.package_required', ) + tuple(clause[1:])]

    @fields.depends('product', 'package', methods=['package'])
    def on_change_product(self):
        try:
            super(Lot, self).on_change_product()
        except AttributeError:
            pass
        if (not self.product or not self.product.default_package
                or (self.package
                    and self.package.product == self.product.template)):
            return
        self.package = self.product.default_package
        self.on_change_package()

    @fields.depends('package')
    def on_change_package(self):
        if self.package:
            if self.package.qty:
                self.package_qty = self.package.qty
            if self.package.weight:
                self.package_weight = self._round_weight(self.package.weight)
            if self.package.pallet_weight:
                self.pallet_weight = self._round_weight(
                    self.package.pallet_weight)
            n_packages = ((self.package.layers or 0)
                * (self.package.packages_layer or 0))
            if n_packages:
                self.initial_number_of_packages = n_packages

    @fields.depends('product')
    def on_change_with_product_uom(self, name=None):
        if not self.product:
            return
        return self.product.default_uom.id

    @staticmethod
    def default_product_unit_digits():
        return 2

    @fields.depends('product', 'product_uom')
    def on_change_with_product_unit_digits(self, name=None):
        self.product_uom = self.on_change_with_product_uom()
        if self.product_uom:
            return self.product_uom.digits
        return self.default_product_unit_digits()

    @property
    def is_weight_uom(self):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        if not self.product:
            return False
        weight_uom_category = ModelData.get_id('product', 'uom_cat_weight')
        return self.product.default_uom.category.id == weight_uom_category

    @fields.depends('package_qty', methods=['weight_by_package'])
    def on_change_with_package_qty(self, name=None):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Uom = pool.get('product.uom')

        self.weight_by_package = self.on_change_with_weight_by_package()
        if self.is_weight_uom and self.weight_by_package:
            kg = Uom(ModelData.get_id('product', 'uom_kilogram'))
            return Uom.compute_qty(kg, self.weight_by_package,
                self.product_uom)
        return self.package_qty

    @fields.depends('initial_number_of_packages', 'package_qty',
        methods=['package_qty', 'product_unit_digits'])
    def on_change_with_total_qty(self, name=None):
        pool = Pool()
        Uom = pool.get('product.uom')

        if any(f is None for f in [
                    self.initial_number_of_packages,
                    self.package_qty]):
            return

        if self.product:
            default_uom = self.product.default_uom
        else:
            default_uom = Uom()
        return default_uom.round(self.initial_number_of_packages *
            self.package_qty)

    @staticmethod
    def default_weight_unit_digits():
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Uom = pool.get('product.uom')
        kg = Uom(ModelData.get_id('product', 'uom_kilogram'))
        return kg.digits + 2

    def get_weight_unit_digits(self, name):
        return self.default_weight_unit_digits()

    @staticmethod
    def _round_weight(weight):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Uom = pool.get('product.uom')
        kg = Uom(ModelData.get_id('product', 'uom_kilogram'))
        return kg.round(weight)

    @fields.depends('gross_weight', 'pallet_weight', 'package_weight',
        'initial_number_of_packages')
    def on_change_with_weight(self, name=None):
        if any(f is None for f in [
                    self.gross_weight,
                    self.pallet_weight,
                    self.package_weight,
                    self.initial_number_of_packages]):
            return
        return self._round_weight(self.gross_weight
            - self.pallet_weight
            - self.package_weight * self.initial_number_of_packages)

    @fields.depends('gross_weight', 'pallet_weight')
    def on_change_with_gross_weight_packages(self, name=None):
        if any(f is None for f in [
                    self.gross_weight,
                    self.pallet_weight]):
            return
        return self._round_weight(self.gross_weight - self.pallet_weight)

    @fields.depends(methods=['total_qty', 'gross_weight_packages'])
    def on_change_with_unit_gross_weight(self, name=None):
        if self.is_weight_uom:
            return

        self.gross_weight_packages = (
            self.on_change_with_gross_weight_packages())
        self.total_qty = self.on_change_with_total_qty()
        if not self.gross_weight_packages or not self.total_qty:
            return 0.0
        return self._round_weight(self.gross_weight_packages / self.total_qty)

    @fields.depends(methods=['total_qty', 'weight'])
    def on_change_with_unit_weight(self, name=None):
        if self.is_weight_uom:
            return

        self.weight = self.on_change_with_weight()
        self.total_qty = self.on_change_with_total_qty()
        if not self.weight or not self.total_qty:
            return 0.0
        return self._round_weight(self.weight / self.total_qty)

    @fields.depends('initial_number_of_packages', methods=['weight'])
    def on_change_with_weight_by_package(self, name=None):
        self.weight = self.on_change_with_weight()
        if not self.initial_number_of_packages:
            return self.weight
        if not self.weight:
            return self.weight
        return self._round_weight(self.weight
            / float(self.initial_number_of_packages))

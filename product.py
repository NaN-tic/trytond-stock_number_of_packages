# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

from .move import StockMixin

__all__ = ['Template', 'Product']
__metaclass__ = PoolMeta


class Template:
    __name__ = 'product.template'
    package_required = fields.Boolean('Packaging Requried')
    default_package = fields.Many2One('product.pack', 'Default Packaging',
        domain=[
            ('id', 'in', Eval('packagings'))
            ],
        states={
            'required': Eval('package_required', False),
            'readonly': ~Eval('active'),
            }, depends=['packagings', 'active'])
    number_of_packages = fields.Function(fields.Float('Number of packages',
            states={
                'invisible': ~Eval('package_required', False),
                }, depends=['package_required']),
        'sum_product')
    forecast_number_of_packages = fields.Function(
        fields.Float('Forecast Number of packages', states={
                'invisible': ~Eval('package_required', False),
                }, depends=['package_required']),
        'sum_product')

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        cls._error_messages.update({
                'change_package_required': (
                    'You cannot change the Packaging Required for a product '
                    'which is associated to stock moves.'),
                })
        cls._modify_no_move.append(
            ('package_required', 'change_package_required'))

    def sum_product(self, name):
        if name in ('number_of_packages', 'forecast_number_of_packages'):
            sum_ = 0.
            for product in self.products:
                qty = getattr(product, name)
                if qty:
                    sum_ += qty
            return sum_
        return super(Template, self).sum_product(name)


class Product(StockMixin):
    __name__ = 'product.product'

    def get_package_required(self, name):
        return self.template.package_required

    @classmethod
    def search_package_required(cls, name, clause):
        return [('template.package_required', ) + tuple(clause[1:])]

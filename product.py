# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.stock_number_of_packages.move import StockMixin

__all__ = ['Template', 'Product']

class Template(metaclass=PoolMeta):
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
        cls._modify_no_move.append(
            ('package_required', 'change_package_required'))

    def sum_product(self, name):
        if name not in ('number_of_packages', 'forecast_number_of_packages'):
            return super(Template, self).sum_product(name)
        sum_ = 0. if name != 'cost_value' else Decimal(0)
        for product in self.products:
            sum_ += getattr(product, name)
        return sum_


class Product(StockMixin, metaclass=PoolMeta):
    __name__ = 'product.product'

    def get_package_required(self, name):
        return self.template.package_required

    @classmethod
    def search_package_required(cls, name, clause):
        return [('template.package_required', ) + tuple(clause[1:])]

    @classmethod
    def _quantity_context(cls, name):
        context = super(Product, cls)._quantity_context(name)
        if not context:
            context = {}
        if name.endswith('number_of_packages'):
            context['number_of_packages'] = True
        return context

    @classmethod
    def _get_quantity(cls, records, name, location_ids,
            grouping=('product',), grouping_filter=None, position=-1):

        quantities = super(Product, cls)._get_quantity(records, name,
            location_ids, grouping=grouping,
            grouping_filter=grouping_filter, position=position)

        if name.endswith('number_of_packages'):
            for key, quantity in quantities.items():
                quantities[key] = 0
                if quantity is not None:
                    quantities[key] = int(quantity)
        return quantities

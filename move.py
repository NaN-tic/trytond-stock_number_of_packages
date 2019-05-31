# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, In
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.stock_number_of_packages.package import PackagedMixin

__all__ = ['StockPackagedMixin', 'StockMixin', 'Move', 'MoveLot']


class LotPackagedMixin(object):
    @classmethod
    def __setup__(cls):
        super(LotPackagedMixin, cls).__setup__()
        if hasattr(cls, 'lot'):
            cls.package.states['readonly'] = Bool(Eval('lot'))
            cls.package.depends.append('lot')
            cls.package.on_change.add('lot')
            cls.number_of_packages.on_change.add('lot')

    @fields.depends('package','lot', methods=['on_change_package'])
    def on_change_lot(self):
        try:
            super(LotPackagedMixin, self).on_change_lot()
        except AttributeError:
            pass
        if hasattr(self, 'lot') and getattr(self, 'lot', None):
            if self.lot.package and self.package != self.lot.package:
                self.package = self.lot.package
            elif not self.lot.package and self.package:
                self.package = None
            self.on_change_package()


class StockPackagedMixin(PackagedMixin):

    def check_package(self, quantity):
        if self.number_of_packages and self.number_of_packages < 0:
            raise UserError(gettext(
                'stock_number_of_packages.number_of_packages_positive',
                    line=self.rec_name))
        super(StockPackagedMixin, self).check_package(quantity)


class StockMixin(object):
    package_required = fields.Function(fields.Boolean('Packaging Required'),
        'get_package_required', searcher='search_package_required')
    number_of_packages = fields.Function(fields.Integer('Number of packages',
            states={
                'invisible': ~Eval('package_required', False),
                }, depends=['package_required']),
        'get_quantity', searcher='search_quantity')
    forecast_number_of_packages = fields.Function(
        fields.Integer('Forecast Number of packages', states={
                'invisible': ~Eval('package_required', False),
                }, depends=['package_required']),
        'get_quantity', searcher='search_quantity')

    def get_package_required(self, name):
        raise NotImplementedError

    @classmethod
    def search_package_required(cls, name, clause):
        raise NotImplementedError

    @classmethod
    def _quantity_context(cls, name):
        if name.endswith('number_of_packages'):
            #quantity_fname = name.replace('number_of_packages', 'quantity')
            context = super(StockMixin, cls)._quantity_context(name)
            context['number_of_packages'] = True
            return context
        return super(StockMixin, cls)._quantity_context(name)

class MoveLot(LotPackagedMixin, metaclass=PoolMeta):
    __name__ = 'stock.move'


class Move(StockPackagedMixin, metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def __setup__(cls):
        super(Move, cls).__setup__()
        for fname in ('package', 'number_of_packages'):
            if 'readonly' in getattr(cls, fname).states:
                getattr(cls, fname).states['readonly'] |= In(
                    Eval('state'), ['cancel', 'assigned', 'done'])
            else:
                getattr(cls, fname).states['readonly'] = In(
                    Eval('state'), ['cancel', 'assigned', 'done'])
            getattr(cls, fname).depends.append('state')

        cls._deny_modify_assigned |= set(['number_of_packages',
                'number_of_packages'])

    @classmethod
    def validate(cls, records):
        super(Move, cls).validate(records)
        pool = Pool()
        InventoryLine = pool.get('stock.inventory.line')
        ShipmentOut = pool.get('stock.shipment.out')

        for move in records:
            check = (isinstance(move.shipment, ShipmentOut) or
                isinstance(move.origin, InventoryLine))
            if move.state in ('assigned', 'done'):
                with Transaction().set_context(
                        no_check_quantity_number_of_packages=check):
                    move.check_package(
                        move._get_internal_quantity(move.quantity, move.uom,
                            move.product))



    @classmethod
    def compute_quantities_query(cls, location_ids, with_childs=False,
            grouping=('product',), grouping_filter=None,
            quantity_field='internal_quantity'):

        quantity_field = 'internal_quantity'
        if Transaction().context.get('number_of_packages'):
            quantity_field = 'number_of_packages'

        return super(Move, cls).compute_quantities_query(
            location_ids, with_childs=with_childs, grouping=grouping,
            grouping_filter=grouping_filter, quantity_field=quantity_field)

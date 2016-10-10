# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import math
from sql import Cast, Column, Join, Literal, Select, Table, Union
from sql.aggregate import Sum
from sql.conditionals import Coalesce
from sql.operators import Neg

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, In
from trytond.transaction import Transaction

from .package import PackagedMixin

__all__ = ['StockPackagedMixin', 'StockMixin', 'Move']
__metaclass__ = PoolMeta


class StockPackagedMixin(PackagedMixin):

    @classmethod
    def __setup__(cls):
        super(StockPackagedMixin, cls).__setup__()
        if hasattr(cls, 'lot'):
            cls.package.states['readonly'] = Bool(Eval('lot'))
            cls.package.depends.append('lot')
            cls.package.on_change.add('lot')
            if cls.quantity.on_change:
                cls.quantity.on_change.add('lot')
            cls.number_of_packages.on_change.add('lot')

    @fields.depends('lot', 'package', methods=['package'])
    def on_change_lot(self):
        try:
            super(StockPackagedMixin, self).on_change_lot()
        except AttributeError:
            pass
        if self.lot:
            if self.lot.package and self.package != self.lot.package:
                self.package = self.lot.package
            elif not self.lot.package and self.package:
                self.package = None
            self.on_change_package()

    def check_package(self, quantity):
        if self.number_of_packages and self.number_of_packages < 0:
            self.raise_user_error('number_of_packages_positive', self.rec_name)
        super(StockPackagedMixin, self).check_package(quantity)


class StockMixin:
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
            quantity_fname = name.replace('number_of_packages', 'quantity')
            context = super(StockMixin, cls)._quantity_context(quantity_fname)
            context['number_of_packages'] = True
            return context
        return super(StockMixin, cls)._quantity_context(name)

    @classmethod
    def _get_quantity(cls, records, name, location_ids, products=None,
            grouping=('product',), position=-1):
        quantities = super(StockMixin, cls)._get_quantity(records, name,
            location_ids, products=products, grouping=grouping,
            position=position)
        if name.endswith('number_of_packages'):
            for key, quantity in quantities.iteritems():
                if quantity != None:
                    quantities[key] = int(quantity)
        return quantities


class Move(StockPackagedMixin):
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

        cls._error_messages.update({
                'package_required': 'Package required for move "%s".',
                'number_of_packages_required': (
                    'Number of packages required for move "%s".'),
                'number_of_packages_positive': (
                    'Number of packages must be positive in move "%s".'),
                'invalid_lot_package': ('Package of move "%s" is not the same '
                    'that the lot\'s package.'),
                'lot_package_qty_required': ('Quantity by Package is required '
                    'for lot "%(lot)s" of move "%(record)s".'),
                'package_qty_required': ('Quantity by Package is required '
                    'for package "%(package)s" of move "%(record)s".'),
                'invalid_quantity_number_of_packages': ('The quantity of move '
                    '"%s" do not correspond to the number of packages.')
                })

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
            grouping=('product',), grouping_filter=None):
        pool = Pool()
        Period = pool.get('stock.period')

        query = super(Move, cls).compute_quantities_query(
            location_ids, with_childs=with_childs, grouping=grouping,
            grouping_filter=grouping_filter)

        if query and Transaction().context.get('number_of_packages'):
            tables_to_find = [cls._table]
            for grouping in Period.groupings():
                Cache = Period.get_cache(grouping)
                if Cache:
                    tables_to_find.append(Cache._table)

            def number_of_packages_column(table):
                if table._name != cls._table:
                    return Cast(
                        Coalesce(table.number_of_packages, Literal(0)),
                        cls.internal_quantity.sql_type().base)
                return Cast(
                    Sum(Coalesce(table.number_of_packages, Literal(0))),
                    cls.internal_quantity.sql_type().base)

            def find_table(join):
                if not isinstance(join, Join):
                    return
                for pos in ['left', 'right']:
                    item = getattr(join, pos)
                    if isinstance(item, Table):
                        if item._name in tables_to_find:
                            return getattr(join, pos)
                    else:
                        return find_table(item)

            def find_queries(query):
                if isinstance(query, Union):
                    for sub_query in query.queries:
                        for q in find_queries(sub_query):
                            yield q
                elif isinstance(query, Select):
                    yield query

            union, = query.from_
            for sub_query in find_queries(union):
                # Find move table
                for table in sub_query.from_:
                    if (isinstance(table, Table)
                            and table._name in tables_to_find):
                        n_packages_col = number_of_packages_column(table)
                        break
                    found = find_table(table)
                    if found:
                        n_packages_col = number_of_packages_column(found)
                        break
                else:
                    # Not query on move table
                    continue

                columns = []
                for col in sub_query.columns:
                    col_name = (col.name if isinstance(col, Column)
                        else col.output_name)
                    if col_name == 'quantity':
                        if isinstance(col.expression, Neg):
                            columns.append(
                                (-n_packages_col).as_('quantity'))
                        else:
                            columns.append(
                                n_packages_col.as_('quantity'))
                    else:
                        columns.append(col)
                sub_query.columns = tuple(columns)
        return query

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        try:
            Lot = pool.get('stock.lot')
        except:
            Lot = None
        Package = pool.get('product.pack')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        if Transaction().context.get('update_packages'):
            for vals in vlist:
                product = Product(vals['product'])
                lot = Lot(vals['lot']) if vals.get('lot') else None
                package = lot.package if lot else (Package(vals['package'])
                    if vals.get('package') else None)

                if not package and not product.package_required:
                    continue
                if not package:
                    package = product.default_package
                vals['package'] = package.id

                if 'number_of_packages' not in vals:
                    if lot:
                        package_qty = lot.package_qty
                    else:
                        package_qty = package.qty
                    if not package_qty:
                        continue

                    quantity = Uom.compute_qty(Uom(vals['uom']),
                        vals['quantity'], product.default_uom)
                    vals['number_of_packages'] = int(
                        math.ceil(quantity / package_qty))
        return super(Move, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        pool = Pool()
        try:
            Lot = pool.get('stock.lot')
        except:
            Lot = None
        Package = pool.get('product.pack')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        if Transaction().context.get('update_packages'):
            actions = iter(args)
            args = []
            for moves, values in zip(actions, actions):
                moves_by_key = {}
                for move in moves:
                    key = (
                        values.get('product', move.product),
                        values.get('lot', getattr(move, 'lot', None)),
                        values.get('package', move.package),
                        values.get('uom', move.uom),
                        values.get('quantity', move.quantity),
                        )
                    moves_by_key.setdefault(key, []).append(move)

                for key, moves in moves_by_key.iteritems():
                    product = key[0]
                    if not isinstance(product, Product):
                        product = Product(product)
                    lot = key[1]
                    if lot and not isinstance(lot, Lot):
                        lot = Lot(lot)
                    package = lot.package if lot else key[2]
                    if package and not isinstance(package, Package):
                        package = Package(package)

                    if not package and not product.package_required:
                        args.extend((moves, values))
                        continue

                    uom = key[3]
                    if not isinstance(uom, Uom):
                        uom = Uom(uom)
                    quantity = key[4]

                    if not package:
                        package = product.default_package
                    new_values = values.copy()
                    new_values['package'] = package.id

                    if lot:
                        package_qty = lot.package_qty
                    else:
                        package_qty = package.qty
                    quantity = Uom.compute_qty(uom, quantity,
                        product.default_uom)
                    new_values['number_of_packages'] = int(
                        math.ceil(quantity / package_qty))
                    args.extend((moves, new_values))
        super(Move, cls).write(*args)

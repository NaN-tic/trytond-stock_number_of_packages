# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import math
from sql import Cast, Join, Literal, Select, Table, Union
from sql.aggregate import Sum
from sql.conditionals import Coalesce
from sql.operators import Neg


from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, In
from trytond.transaction import Transaction

__all__ = ['StockPackagedMixin', 'StockMixin', 'Move']
__metaclass__ = PoolMeta


STATES = {
    'invisible': ~Bool(Eval('product')),
}
DEPENDS = ['product']


class StockPackagedMixin:
    package = fields.Many2One('product.pack', 'Packaging', domain=[
            ('product.products', 'in', [Eval('product')]),
            ],
        states=STATES, depends=DEPENDS)
    number_of_packages = fields.Integer('Number of packages', states=STATES,
        depends=DEPENDS)

    @classmethod
    def __setup__(cls):
        super(StockPackagedMixin, cls).__setup__()
        if hasattr(cls, 'lot'):
            cls.package.states['readonly'] = Bool(Eval('lot'))
            cls.package.depends.append('lot')

    @fields.depends('product', 'package', methods=['package'])
    def on_change_product(self):
        res = super(StockPackagedMixin, self).on_change_product()
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

    @fields.depends('lot', 'package', methods=['package'])
    def on_change_lot(self):
        try:
            res = super(StockPackagedMixin, self).on_change_lot()
        except AttributeError:
            res = {}
        if self.lot and self.lot.package and self.package != self.lot.package:
            res['package'] = self.lot.package.id
            res['package.rec_name'] = (
                self.lot.package.rec_name)
            self.package = self.lot.package
            res.update(self.on_change_package())
        elif self.lot and not self.lot.package and self.package:
            res['package'] = None
            res['package.rec_name'] = None
        return res

    @fields.depends('lot', 'package', 'number_of_packages',
            methods=['quantity'])
    def on_change_package(self):
        if getattr(self, 'lot', None):
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

    @fields.depends('quantity', 'package', 'lot')
    def on_change_quantity(self):
        if getattr(self, 'lot', None):
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
            res = super(StockPackagedMixin, self).on_change_quantity()
        except AttributeError:
            res = {}
        res.update({
                'number_of_packages': self.number_of_packages,
                'quantity': self.quantity,
                })
        return res

    @fields.depends('lot', 'package', 'number_of_packages')
    def on_change_number_of_packages(self):
        if self.number_of_packages is None:
            return {}
        if getattr(self, 'lot', None):
            package_qty = self.lot.package_qty
        elif self.package and self.package.qty:
            package_qty = self.package.qty
        else:
            return {}
        return {
            'quantity': package_qty * self.number_of_packages
            }

    def check_package(self, quantity):
        """
        Check if package is required and all realted data is exists, and
        if number of packages corresponds to the quantity.
        """
        if (not self.product.package_required
                or self.quantity < self.uom.rounding):
            return

        if not self.package:
            self.raise_user_error('package_required', self.rec_name)

        if self.number_of_packages == None:
            self.raise_user_error('number_of_packages_required', self.rec_name)
        elif self.number_of_packages < 0:
            self.raise_user_error('number_of_packages_positive', self.rec_name)

        if getattr(self, 'lot', None):
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
        for move in records:
            if move.state in ('assigned', 'done'):
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
                    if col.output_name == 'quantity':
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

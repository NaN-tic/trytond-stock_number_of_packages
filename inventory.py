# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

from .move import StockPackagedMixin, LotPackagedMixin

__all__ = ['Inventory', 'InventoryLine']


class Inventory(metaclass=PoolMeta):
    __name__ = 'stock.inventory'

    @classmethod
    def grouping(cls):
        return super(Inventory, cls).grouping() + ('package', )

    @classmethod
    def confirm(cls, inventories):
        with Transaction().set_context(
                no_check_quantity_number_of_packages=True):
            super(Inventory, cls).confirm(inventories)

    @classmethod
    def complete_lines(cls, inventories, fill=True):
        pool = Pool()
        Category = pool.get('product.category')
        Line = pool.get('stock.inventory.line')
        Product = pool.get('product.product')

        super(Inventory, cls).complete_lines(inventories, fill)

        grouping = cls.grouping()
        to_create = []
        for inventory in inventories:
            # Compute product number of packages
            product_ids = None
            if getattr(inventory, 'product_category', None):
                categories = Category.search([
                        ('parent', 'child_of',
                            [inventory.product_category.id]),
                        ])
                products = Product.search([('categories.id', 'in', [
                    x.id for x in categories])])
                product_ids = [p.id for p in products]
            if not product_ids:
                continue

            with Transaction().set_context(
                    stock_date_end=inventory.date,
                    number_of_packages=True):
                pbl = Product.products_by_location(
                    [inventory.location.id],
                    grouping=grouping, grouping_filter=(product_ids,))

            # Index some data
            product2type = {}
            product2consumable = {}
            for product in Product.browse([line[1] for line in pbl]):
                product2type[product.id] = product.type
                product2consumable[product.id] = product.consumable

            # Update existing lines
            to_write = []
            for line in inventory.lines:
                if not line.package:
                    continue
                key = (inventory.location.id,) + line.unique_key
                if key in pbl:
                    number_of_packages = int(pbl.pop(key))
                else:
                    number_of_packages = 0
                if (line.number_of_packages == line.expected_number_of_packages):
                    continue
                values = {
                    'expected_number_of_packages': number_of_packages,
                    }
                if (getattr(inventory, 'init_quantity_zero', False)
                        and line.quantity == 0):
                    values['number_of_packages'] = 0
                elif (line.number_of_packages == None
                        or line.number_of_packages
                        == line.expected_number_of_packages):
                    values['number_of_packages'] = max(number_of_packages, 0)
                to_write.extend(([line], values))
            if to_write:
                Line.write(*to_write)

            if not fill:
                continue

            # Create lines if needed
            for key, number_of_packages in pbl.items():
                product_id = key[grouping.index('product') + 1]
                if not number_of_packages:
                    continue
                if (product2type[product_id] != 'goods'
                        or product2consumable[product_id]):
                    continue

                values = Line.create_values4complete(inventory, 0.)
                for i, fname in enumerate(grouping, 1):
                    values[fname] = key[i]
                values['expected_number_of_packages'] = int(number_of_packages)
                if getattr(inventory, 'init_quantity_zero', False):
                    values['number_of_packages'] = 0
                else:
                    values['number_of_packages'] = max(
                        int(number_of_packages), 0)
                to_create.append(values)
        if to_create:
            Line.create(to_create)


class LotInventoryLine(LotPackagedMixin, metaclass=PoolMeta):
    __name__ = 'stock.inventory.line'


class InventoryLine(StockPackagedMixin, metaclass=PoolMeta):
    __name__ = 'stock.inventory.line'

    expected_number_of_packages = fields.Integer('Expected Number of packages',
        readonly=True)

    @staticmethod
    def default_expected_number_of_packages():
        return 0

    @fields.depends('inventory', '_parent_inventory.date',
        '_parent_inventory.location', 'product', 'package',
        methods=['_compute_expected_number_of_packages'])
    def on_change_with_expected_number_of_packages(self):
        if not self.inventory or not self.product:
            return
        return self._compute_expected_number_of_packages(
            self.inventory,
            self.product.id,
            (self.lot.id if hasattr(self, 'lot') and
                getattr(self, 'lot', None) else None),
            self.package.id if self.package else None)

    def get_move(self):
        pool = Pool()
        Move = pool.get('stock.move')

        move = super(InventoryLine, self).get_move()
        if not move:
            return

        if not self.product.package_required and not self.package:
            return move

        if (self.number_of_packages is None
                and self.inventory.empty_quantity == 'keep'):
            return move

        delta_number_of_packages = ((self.expected_number_of_packages or 0)
            - (self.number_of_packages or 0))
        if not move and delta_number_of_packages:
            from_location = self.inventory.location
            to_location = self.inventory.lost_found
            if delta_number_of_packages < 0:
                (from_location, to_location) = (to_location, from_location)
            move = Move(
                from_location=from_location,
                to_location=to_location,
                quantity=0.0,
                product=self.product,
                uom=self.uom,
                company=self.inventory.company,
                effective_date=self.inventory.date,
                origin=self,
                )
            if getattr(self, 'lot', None):
                move.lot = self.lot
        elif not move:
            return

        move.package = self.package
        move.number_of_packages = int(abs(delta_number_of_packages))
        return move

    @classmethod
    def validate(cls, records):
        super(InventoryLine, cls).validate(records)
        for line in records:
            if line.inventory.state == 'done':
                line.check_package(line.quantity)

    @classmethod
    def create(cls, vlist):
        for values in vlist:
            if 'expected_number_of_packages' not in values:
                values['expected_number_of_packages'] = int(
                    cls._compute_expected_number_of_packages(
                        values.get('inventory'),
                        values.get('product'),
                        values.get('lot'),
                        values.get('package')))

        return super(InventoryLine, cls).create(vlist)

    @staticmethod
    def _compute_expected_number_of_packages(inventory, product_id, lot_id,
            package_id):
        pool = Pool()
        Inventory = pool.get('stock.inventory')
        Product = pool.get('product.product')

        if not isinstance(inventory, Inventory):
            inventory = Inventory(inventory)

        if not inventory or not inventory.location:
            return 0

        if 'lot' in Inventory.grouping():
            grouping = ('product', 'lot', 'package')
            key = (inventory.location.id, product_id, lot_id, package_id)
        else:
            grouping = ('product', 'package')
            key = (inventory.location.id, product_id, package_id)

        with Transaction().set_context(
                stock_date_end=inventory.date,
                number_of_packages=True):
            pbl = Product.products_by_location(
                [inventory.location.id], grouping_filter=([product_id],),
                grouping=grouping)

        if key in pbl:
            return int(pbl.pop(key) or 0)
        return 0

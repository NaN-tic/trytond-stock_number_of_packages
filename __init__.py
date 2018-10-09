# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import package
from . import product
from . import move
from . import period
from . import lot
from . import shipment
from . import inventory
from . import location


def register():
    Pool.register(
        move.Move,
        package.ProductPack,
        product.Template,
        product.Product,
        period.Period,
        period.PeriodCache,
        period.PeriodCachePackage,
        shipment.ShipmentIn,
        shipment.ShipmentOut,
        shipment.ShipmentOutReturn,
        inventory.Inventory,
        inventory.InventoryLine,
        location.Location,
        module='stock_number_of_packages', type_='model')
    Pool.register(
        lot.Lot,
        move.MoveLot,
        inventory.LotInventoryLine,
        period.PeriodCacheLot,
        depends=['stock_lot'],
        module='stock_number_of_packages', type_='model')

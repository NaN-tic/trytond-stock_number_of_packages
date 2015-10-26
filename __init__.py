# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .product import *
from .move import *
from .period import *
from .lot import *
from .shipment import *
from .inventory import *
from .location import *


def register():
    Pool.register(
        Template,
        Product,
        ProductPack,
        Move,
        Period,
        PeriodCache,
        PeriodCacheLot,
        PeriodCachePackage,
        Lot,
        ShipmentIn,
        ShipmentOut,
        ShipmentOutReturn,
        Inventory,
        InventoryLine,
        Location,
        module='stock_number_of_packages', type_='model')

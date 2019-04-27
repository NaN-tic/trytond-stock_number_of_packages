# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['ShipmentIn', 'ShipmentOut', 'ShipmentOutReturn']


class ShipmentIn(metaclass=PoolMeta):
    __name__ = 'stock.shipment.in'

    def _get_inventory_move(self, incoming_move):
        move = super(ShipmentIn, self)._get_inventory_move(incoming_move)
        if not move:
            return
        move.package = incoming_move.package
        move.number_of_packages = incoming_move.number_of_packages
        return move


class ShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    def _get_inventory_move(self, move):
        inventory_move = super(ShipmentOut, self)._get_inventory_move(move)
        if not inventory_move:
            return
        inventory_move.package = move.package
        inventory_move.number_of_packages = move.number_of_packages
        return inventory_move

    @classmethod
    def pack(cls, shipments):
        with Transaction().set_context(
                no_check_quantity_number_of_packages=Transaction().context.get(
                    'no_check_quantity_number_of_packages', True)):
            super(ShipmentOut, cls).pack(shipments)

    def _get_outgoing_move(self, move):
        new_move = super(ShipmentOut, self)._get_outgoing_move(move)
        if not new_move:
            return
        new_move.package = move.package
        # new_move.number_of_packages = move.number_of_packages
        return new_move

    @classmethod
    def done(cls, shipments):
        # TODO: improve _sync_inventory_to_outgoing to match
        # quantity == number_of_packages * package_qty
        with Transaction().set_context(
                no_check_quantity_number_of_packages=True):
            super(ShipmentOut, cls).done(shipments)


class ShipmentOutReturn(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.return'

    @classmethod
    def _get_inventory_moves(cls, incoming_move):
        move = super(ShipmentOutReturn,
            cls)._get_inventory_moves(incoming_move)
        if move and incoming_move.package:
            move.package = incoming_move.package
            move.number_of_packages = incoming_move.number_of_packages
        return move

# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.transaction import Transaction

__all__ = ['Location']


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'
    number_of_packages = fields.Function(fields.Integer('Number of packages'),
        'get_number_of_packages')
    forecast_number_of_packages = fields.Function(
        fields.Integer('Forecast Number of packages'),
        'get_number_of_packages')

    @classmethod
    def get_number_of_packages(cls, locations, name):
        quantity_fname = name.replace('number_of_packages', 'quantity')
        with Transaction().set_context(number_of_packages=True):
            quantities = cls.get_quantity(locations, quantity_fname)
        for key, quantity in quantities.iteritems():
            if quantity != None:
                quantities[key] = int(quantity)
        return quantities

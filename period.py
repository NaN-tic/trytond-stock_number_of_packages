# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Period', 'PeriodCache', 'PeriodCacheLot', 'PeriodCachePackage']


class NumberOfPackagesCacheMixin(object):
    number_of_packages = fields.Integer('Number of packages', readonly=True)

    @classmethod
    def compute_number_of_packages(cls, vlist, grouping):
        pool = Pool()
        Period = pool.get('stock.period')
        Product = pool.get('product.product')

        vlist_by_period_location = {}
        for values in vlist:
            vlist_by_period_location.setdefault(values['period'], {})\
                .setdefault(values['location'], []).append(values)

        vlist = []
        for period_id, vlist_by_location in \
                vlist_by_period_location.iteritems():
            period = Period(period_id)
            with Transaction().set_context(
                    stock_date_end=period.date,
                    stock_date_start=None,
                    stock_assign=False,
                    forecast=False,
                    stock_destinations=None,
                    number_of_packages=True,
                    ):
                pbl = Product.products_by_location(
                    vlist_by_location.keys(), grouping=grouping)
            for location_id, location_vlist in vlist_by_location.iteritems():
                for values in location_vlist:
                    key = tuple([location_id] + [values[x] for x in grouping])
                    values['number_of_packages'] = int(pbl.get(key, 0.0))
                    vlist.append(values)
        return vlist


class Period(metaclass=PoolMeta):
    __name__ = 'stock.period'

    package_caches = fields.One2Many('stock.period.cache.package', 'period',
        'Package Caches', readonly=True)

    @classmethod
    def groupings(cls):
        return super(Period, cls).groupings() + [('product', 'package')]

    @classmethod
    def get_cache(cls, grouping):
        pool = Pool()
        Cache = super(Period, cls).get_cache(grouping)
        if grouping == ('product', 'package'):
            return pool.get('stock.period.cache.package')
        return Cache


class PeriodCache(NumberOfPackagesCacheMixin, metaclass=PoolMeta):
    __name__ = 'stock.period.cache'

    @classmethod
    def create(cls, vlist):
        vlist = cls.compute_number_of_packages(vlist, ('product',))
        return super(PeriodCache, cls).create(vlist)


class PeriodCacheLot(NumberOfPackagesCacheMixin, metaclass=PoolMeta):
    __name__ = 'stock.period.cache.lot'

    @classmethod
    def create(cls, vlist):
        vlist = cls.compute_number_of_packages(vlist, ('product', 'lot'))
        return super(PeriodCacheLot, cls).create(vlist)


class PeriodCachePackage(ModelSQL, ModelView, NumberOfPackagesCacheMixin):
    '''
    Stock Period Cache per Package

    It is used to store cached computation of stock quantities per package.
    '''
    __name__ = 'stock.period.cache.package'
    period = fields.Many2One('stock.period', 'Period', required=True,
        readonly=True, select=True, ondelete='CASCADE')
    location = fields.Many2One('stock.location', 'Location', required=True,
        readonly=True, select=True, ondelete='CASCADE')
    product = fields.Many2One('product.product', 'Product', required=True,
        readonly=True, ondelete='CASCADE')
    package = fields.Many2One('product.pack', 'Package', readonly=True,
        ondelete='CASCADE')
    internal_quantity = fields.Float('Internal Quantity', readonly=True)

    @classmethod
    def create(cls, vlist):
        vlist = cls.compute_number_of_packages(vlist,
            ('product', 'package'))
        return super(PeriodCachePackage, cls).create(vlist)

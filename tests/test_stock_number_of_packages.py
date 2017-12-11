# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import doctest
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
from trytond.tests.test_tryton import doctest_checker
from trytond.tests.test_tryton import install_module, drop_create


class StockNumberOfPackagesTestCase(ModuleTestCase):
    'Test Stock Number of Packages module'
    module = 'stock_number_of_packages'

    @classmethod
    def setUpClass(cls):
        drop_create()
        super(ModuleTestCase, cls).setUpClass()
        install_module('stock_lot')


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            StockNumberOfPackagesTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_stock_number_of_packages.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    suite.addTests(doctest.DocFileSuite(
            'scenario_stock_number_of_packages_extra_depends.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite

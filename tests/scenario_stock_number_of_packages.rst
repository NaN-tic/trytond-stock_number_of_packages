===========================
Number of packages Scenario
===========================

=============
General Setup
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()
    >>> last_month = today - relativedelta(months=1)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install stock_number_of_packages Module::

    >>> Module = Model.get('ir.module.module')
    >>> stock_module, = Module.find([('name', '=', 'stock_number_of_packages')])
    >>> stock_module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='US Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> kg, = ProductUom.find([('name', '=', 'Kilogram')])
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> template = ProductTemplate()
    >>> template.name = 'Product without Package'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> package = template.packagings.new()
    >>> package.name = 'Package 1'
    >>> package.qty = 6
    >>> package.weight = 0.3
    >>> template.save()
    >>> product_wo_package, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'Product with Package'
    >>> template.default_uom = kg
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> package = template.packagings.new()
    >>> package.name = 'Package 1'
    >>> package.qty = 4.5
    >>> package.weight = 0.3
    >>> package = template.packagings.new()
    >>> package.name = 'Package 2'
    >>> package.qty = 5.5
    >>> package.weight = 0.3
    >>> package = template.packagings.new()
    >>> package.name = 'Package 3'
    >>> package.weight = 0.4
    >>> template.save()
    >>> template.package_required = True
    >>> template.default_package = template.packagings[0]
    >>> template.save()
    >>> product_w_package, = template.products

Search by package required::

    >>> Product = Model.get('product.product')
    >>> len(Product.find([('package_required', '=', True)]))
    1

Receive products one month ago::

    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment_in = ShipmentIn()
    >>> shipment_in.supplier = supplier
    >>> shipment_in.effective_date = last_month
    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product_wo_package
    >>> incoming_move.quantity = 100
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input

    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product_w_package
    >>> incoming_move.number_of_packages = 10
    >>> incoming_move.quantity
    45.0
    >>> incoming_move.quantity = 50.0
    >>> incoming_move.number_of_packages
    12
    >>> incoming_move.quantity
    54.0
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input

    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product_w_package
    >>> incoming_move.number_of_packages = 4
    >>> incoming_move.quantity
    18.0
    >>> incoming_move.package = product_w_package.template.packagings[1]
    >>> incoming_move.quantity = 22.0
    >>> incoming_move.number_of_packages
    4
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input
    >>> shipment_in.save()
    >>> shipment_in.click('receive')
    >>> shipment_in.click('done')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    100.0
    0
    76.0
    16

Create an inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> inventory = Inventory()
    >>> inventory.date = last_month + relativedelta(days=5)
    >>> inventory.location = storage_loc
    >>> line = inventory.lines.new()
    >>> line.product = product_w_package
    >>> line.number_of_packages = 11
    >>> inventory.save()
    >>> inventory.click('complete_lines')
    >>> len(inventory.lines)
    3
    >>> for line in inventory.lines:
    ...     if line.product == product_wo_package:
    ...         line.expected_quantity == 100.0
    ...         line.expected_number_of_packages == 0
    ...         line.quantity = 80.0
    ...     elif (line.product == product_w_package
    ...             and line.package == product_w_package.template.default_package):
    ...         line.expected_quantity == 54.0
    ...         line.expected_number_of_packages == 12
    ...         line.number_of_packages == 11
    ...         line.quantity == 49.5
    ...     elif line.product == product_w_package:
    ...         line.package == product_w_package.template.packagings[1]
    ...         line.expected_quantity == 22.0
    ...         line.expected_number_of_packages == 4
    ...         line.number_of_packages = 6
    True
    True
    True
    True
    True
    True
    True
    True
    True
    >>> inventory.save()
    >>> inventory.click('confirm')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    80.0
    0
    82.5
    17

Create a period::

    >>> Period = Model.get('stock.period')
    >>> period = Period()
    >>> period.date = last_month + relativedelta(days=10)
    >>> period.company = company
    >>> period.save()
    >>> period.click('close')
    >>> period.reload()
    >>> for cache in period.caches:
    ...     if (cache.product == product_wo_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 80.0
    ...         cache.number_of_packages == 0
    ...     elif (cache.product == product_w_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 82.5
    ...         cache.number_of_packages == 17
    True
    True
    True
    True
    >>> for cache in period.package_caches:
    ...     if (cache.product == product_wo_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 80.0
    ...         cache.number_of_packages == 0
    ...     elif (cache.product == product_w_package
    ...             and cache.package == product_w_package.template.default_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 49.5
    ...         cache.number_of_packages == 11
    ...     elif (cache.product == product_w_package
    ...             and cache.package == product_w_package.template.packagings[1]
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 33.0
    ...         cache.number_of_packages == 6
    True
    True
    True
    True
    True
    True

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    80.0
    0
    82.5
    17

Create Shipment Out::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out = ShipmentOut()
    >>> shipment_out.planned_date = today
    >>> shipment_out.customer = customer
    >>> outgoing_move = shipment_out.outgoing_moves.new()
    >>> outgoing_move.product = product_wo_package
    >>> outgoing_move.quantity = 40
    >>> outgoing_move.from_location = shipment_out.warehouse_output
    >>> outgoing_move.to_location = customer_loc
    >>> outgoing_move = shipment_out.outgoing_moves.new()
    >>> outgoing_move.product = product_w_package
    >>> outgoing_move.number_of_packages = 5
    >>> outgoing_move.from_location = shipment_out.warehouse_output
    >>> outgoing_move.to_location = customer_loc
    >>> shipment_out.save()

Set the shipment state to waiting::

    >>> shipment_out.click('wait')
    >>> len(shipment_out.inventory_moves)
    2

Assign the shipment::

    >>> for inventory_move in shipment_out.inventory_moves:
    ...     if inventory_move.product == product_w_package:
    ...         inventory_move.number_of_packages = 4
    >>> inventory_move = shipment_out.inventory_moves.new()
    >>> inventory_move.product = product_w_package
    >>> inventory_move.package = product_w_package.template.packagings[1]
    >>> inventory_move.number_of_packages = 1
    >>> inventory_move.quantity
    5.5
    >>> inventory_move.from_location = shipment_out.warehouse_storage
    >>> inventory_move.to_location = shipment_out.warehouse_output
    >>> shipment_out.save()
    >>> shipment_out.click('assign_try')
    True

Check available quantities and forecast quantities by product::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_wo_package.forecast_quantity
    ...     product_wo_package.forecast_number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    ...     product_w_package.forecast_quantity
    ...     product_w_package.forecast_number_of_packages
    80.0
    0
    40.0
    0
    82.5
    17
    59.0
    12

Check available quantities in location::

    >>> with config.set_context({'product': product_w_package.id, 'stock_date_end': today}):
    ...     storage_loc.reload()
    ...     storage_loc.quantity
    ...     storage_loc.number_of_packages
    ...     storage_loc.forecast_quantity
    ...     storage_loc.forecast_number_of_packages
    82.5
    17
    59.0
    12

Finalize the shipment::

    >>> shipment_out.reload()
    >>> shipment_out.click('pack')
    >>> shipment_out.reload()

.. The outgoing moves doesn't mantain the package information when it doesn't use lot
..     >>> for outgoing_move in shipment_out.outgoing_moves:
..     ...     if outgoing_move.product == product_wo_package:
..     ...         outgoing_move.number_of_packages == None
..     ...     elif (outgoing_move.product == product_w_package
..     ...             and outgoing_move.package == product_w_package.template.default_package):
..     ...         outgoing_move.number_of_packages == 4
..     ...     else:
..     ...         outgoing_move.number_of_packages == 1
..     True
..     True
..     True

    >>> shipment_out.click('done')

Create Shipment Out Return::

    >>> ShipmentOutReturn = Model.get('stock.shipment.out.return')
    >>> shipment_out_return = ShipmentOutReturn()
    >>> shipment_out_return.customer = customer
    >>> incoming_move = shipment_out_return.incoming_moves.new()
    >>> incoming_move.product = product_wo_package
    >>> incoming_move.quantity = 25
    >>> incoming_move.from_location = customer_loc
    >>> incoming_move.to_location = shipment_out_return.warehouse_input
    >>> incoming_move = shipment_out_return.incoming_moves.new()
    >>> incoming_move.product = product_w_package
    >>> incoming_move.number_of_packages = 1
    >>> incoming_move.from_location = customer_loc
    >>> incoming_move.to_location = shipment_out_return.warehouse_input
    >>> shipment_out_return.save()
    >>> shipment_out_return.click('receive')
    >>> shipment_out_return.click('done')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    65.0
    0
    63.5
    13

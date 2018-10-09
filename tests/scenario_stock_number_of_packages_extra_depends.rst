==============================================
Number of packages Scenario with extra depends
==============================================

=============
General Setup
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()
    >>> last_month = today - relativedelta(months=1)


Install stock_number_of_packages Module::

    >>> config = activate_modules('stock_number_of_packages', 'stock_lot', 
    ...     'stock_inventory_product_category', 'stock_lot_quantit', 'sale',
    ...     'purchase'])

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> party = company.party

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> cash = accounts['cash']

    >>> Journal = Model.get('account.journal')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

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
    >>> template.default_uom = kg
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> package = template.packagings.new()
    >>> package.name = 'Package 1'
    >>> package.qty = 6.0
    >>> package.weight = 0.3
    >>> template.save()
    >>> template.default_package = template.packagings[0]
    >>> template.save()
    >>> product_wo_package, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'Product with Package'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> package = template.packagings.new()
    >>> package.name = 'Package 1'
    >>> package.qty = 4
    >>> package.weight = 0.3
    >>> package = template.packagings.new()
    >>> package.name = 'Package 2'
    >>> package.qty = 5
    >>> package.weight = 0.3
    >>> package = template.packagings.new()
    >>> package.name = 'Package 3'
    >>> package.weight = 0.4
    >>> template.save()
    >>> template.package_required = True
    >>> template.default_package = template.packagings[0]
    >>> template.save()
    >>> product_w_package, = template.products

    >>> LotType = Model.get('stock.lot.type')
    >>> for lot_type in LotType.find([]):
    ...     template.lot_required.append(lot_type)

    >>> template = ProductTemplate()
    >>> template.name = 'Product with Lot without Package'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> for lot_type in LotType.find([]):
    ...     template.lot_required.append(lot_type)
    >>> package = template.packagings.new()
    >>> package.name = 'Package 1'
    >>> package.qty = 6
    >>> package.weight = 0.3
    >>> template.save()
    >>> template.default_package = template.packagings[0]
    >>> template.save()
    >>> product_lot_wo_package, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'Product with Lot with Package'
    >>> template.default_uom = kg
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> for lot_type in LotType.find([]):
    ...     template.lot_required.append(lot_type)
    >>> package = template.packagings.new()
    >>> package.name = 'Package 1'
    >>> package.qty = 4.5
    >>> package.weight = 0.3
    >>> package = template.packagings.new()
    >>> package.name = 'Package 2'
    >>> package.weight = 0.4
    >>> template.save()
    >>> template.package_required = True
    >>> template.default_package = template.packagings[0]
    >>> template.save()
    >>> product_lot_w_package, = template.products

Purchase products two month ago::

    >>> Purchase = Model.get('purchase.purchase')
    >>> purchase = Purchase()
    >>> purchase.party = supplier
    >>> purchase.date = last_month - relativedelta(months=1)
    >>> purchase.payment_term = payment_term
    >>> purchase.invoice_method = 'manual'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_wo_package
    >>> purchase_line.quantity = 100.0
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_w_package
    >>> purchase_line.quantity = 200
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_lot_wo_package
    >>> purchase_line.quantity = 25
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_lot_w_package
    >>> purchase_line.quantity = 75.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.click('process')
    >>> purchase.state
    u'processing'
    >>> len(purchase.moves), len(purchase.shipment_returns)
    (4, 0)

Validate Shipments one month ago::

    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> Move = Model.get('stock.move')
    >>> Lot = Model.get('stock.lot')
    >>> shipment_in = ShipmentIn()
    >>> shipment_in.supplier = supplier
    >>> shipment_in.effective_date = last_month
    >>> moves_by_product = {m.product.id: m for m in purchase.moves}

    >>> incoming_move = Move(id=moves_by_product[product_wo_package.id].id)
    >>> shipment_in.incoming_moves.append(incoming_move)

    >>> incoming_move = Move(id=moves_by_product[product_w_package.id].id)
    >>> new_incoming_move = Move(Move.copy([incoming_move.id], config.context)[0])
    >>> new_incoming_move.package = product_w_package.template.default_package
    >>> new_incoming_move.number_of_packages = 45
    >>> new_incoming_move.quantity
    180.0
    >>> shipment_in.incoming_moves.append(new_incoming_move)

    >>> incoming_move.package = product_w_package.template.packagings[1]
    >>> incoming_move.number_of_packages = 4
    >>> incoming_move.quantity
    20.0
    >>> shipment_in.incoming_moves.append(incoming_move)

    >>> incoming_move = Move(id=moves_by_product[product_lot_wo_package.id].id)
    >>> lot_wo_package = Lot(
    ...     product=product_lot_wo_package,
    ...     number=str(product_lot_wo_package.id))
    >>> lot_wo_package.package == product_lot_wo_package.template.default_package
    True
    >>> lot_wo_package.package_weight
    0.3
    >>> lot_wo_package.package_qty
    6.0
    >>> lot_wo_package.package_qty = 5
    >>> lot_wo_package.initial_number_of_packages = 5
    >>> lot_wo_package.total_qty
    25.0
    >>> lot_wo_package.gross_weight = 31.5
    >>> lot_wo_package.pallet_weight = 10.0
    >>> lot_wo_package.weight
    20.0
    >>> lot_wo_package.weight_by_package
    4.0
    >>> lot_wo_package.unit_weight
    0.8
    >>> lot_wo_package.save()
    >>> incoming_move.lot = lot_wo_package
    >>> incoming_move.package == product_lot_wo_package.template.default_package
    True
    >>> incoming_move.number_of_packages = 5
    >>> incoming_move.quantity
    25.0
    >>> shipment_in.incoming_moves.append(incoming_move)

    >>> incoming_move = Move(id=moves_by_product[product_lot_w_package.id].id)
    >>> lot_w_package = Lot(
    ...     product=product_lot_w_package,
    ...     number=str(product_lot_wo_package.id))
    >>> lot_w_package.package == product_lot_w_package.template.default_package
    True
    >>> lot_w_package.package = product_lot_w_package.template.packagings[1]
    >>> lot_w_package.package_weight
    0.4
    >>> lot_w_package.initial_number_of_packages = 17
    >>> lot_w_package.gross_weight = 96.7
    >>> lot_w_package.pallet_weight = 10.0
    >>> lot_w_package.weight
    79.9
    >>> lot_w_package.weight_by_package
    4.7
    >>> lot_w_package.package_qty
    4.7
    >>> lot_w_package.save()
    >>> incoming_move.lot = lot_w_package
    >>> incoming_move.package == product_lot_w_package.template.packagings[1]
    True
    >>> incoming_move.number_of_packages = 17
    >>> incoming_move.quantity
    79.9
    >>> shipment_in.incoming_moves.append(incoming_move)

    >>> shipment_in.save()
    >>> shipment_in.click('receive')
    >>> shipment_in.click('done')

Check available quantities by product::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    ...     product_lot_wo_package.reload()
    ...     product_lot_wo_package.quantity
    ...     product_lot_wo_package.number_of_packages
    ...     product_lot_w_package.reload()
    ...     product_lot_w_package.quantity
    ...     product_lot_w_package.number_of_packages
    100.0
    0
    200.0
    49
    25.0
    5
    79.9
    17

Check available quantities by lot::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     lot_wo_package.reload()
    ...     lot_wo_package.quantity
    ...     lot_wo_package.number_of_packages
    ...     lot_w_package.reload()
    ...     lot_w_package.quantity
    ...     lot_w_package.number_of_packages
    25.0
    5
    79.9
    17

Create an inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> inventory = Inventory()
    >>> inventory.date = last_month + relativedelta(days=5)
    >>> inventory.location = storage_loc
    >>> inventory.save()
    >>> inventory.click('complete_lines')
    >>> len(inventory.lines)
    5
    >>> lines_by_key = {(l.product.id, l.lot.id if l.lot else None, l.package.id if l.package else None): l for l in inventory.lines}

    >>> line = lines_by_key[(product_wo_package.id, None, None)]
    >>> line.expected_quantity
    100.0
    >>> line.expected_number_of_packages
    0
    >>> line.quantity = 80.0

    >>> line = lines_by_key[(product_w_package.id, None, product_w_package.template.default_package.id)]
    >>> line.expected_quantity
    180.0
    >>> line.expected_number_of_packages
    45
    >>> line.number_of_packages = 48
    >>> line.quantity
    192.0

    >>> line = lines_by_key[(product_w_package.id, None, product_w_package.template.packagings[1].id)]
    >>> line.expected_quantity
    20.0
    >>> line.expected_number_of_packages
    4
    >>> line.number_of_packages = 3
    >>> line.quantity
    15.0

    >>> line = lines_by_key[(product_lot_wo_package.id, lot_wo_package.id, product_lot_wo_package.template.default_package.id)]
    >>> line.expected_quantity
    25.0
    >>> line.expected_number_of_packages
    5
    >>> line.number_of_packages = 6
    >>> line.quantity
    30.0

    >>> line = lines_by_key[(product_lot_w_package.id, lot_w_package.id, product_lot_w_package.template.packagings[1].id)]
    >>> line.expected_quantity
    79.9
    >>> line.expected_number_of_packages
    17
    >>> line.number_of_packages = 19
    >>> line.quantity
    89.3

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
    ...     product_lot_wo_package.reload()
    ...     product_lot_wo_package.quantity
    ...     product_lot_wo_package.number_of_packages
    ...     product_lot_w_package.reload()
    ...     product_lot_w_package.quantity
    ...     product_lot_w_package.number_of_packages
    ...     lot_wo_package.reload()
    ...     lot_wo_package.quantity
    ...     lot_wo_package.number_of_packages
    ...     lot_w_package.reload()
    ...     lot_w_package.quantity
    ...     lot_w_package.number_of_packages
    80.0
    0
    207.0
    51
    30.0
    6
    89.3
    19
    30.0
    6
    89.3
    19

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
    ...         cache.internal_quantity == 207.0
    ...         cache.number_of_packages == 51
    ...     elif (cache.product == product_lot_wo_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 30.0
    ...         cache.number_of_packages == 6
    ...     elif (cache.product == product_lot_w_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 89.3
    ...         cache.number_of_packages == 19
    True
    True
    True
    True
    True
    True
    True
    True
    >>> for cache in period.lot_caches:
    ...     if (cache.lot == lot_wo_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 30.0
    ...         cache.number_of_packages == 6
    ...     elif (cache.lot == lot_w_package
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 89.3
    ...         cache.number_of_packages == 19
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
    ...     product_lot_wo_package.reload()
    ...     product_lot_wo_package.quantity
    ...     product_lot_wo_package.number_of_packages
    ...     product_lot_w_package.reload()
    ...     product_lot_w_package.quantity
    ...     product_lot_w_package.number_of_packages
    ...     lot_wo_package.reload()
    ...     lot_wo_package.quantity
    ...     lot_wo_package.number_of_packages
    ...     lot_w_package.reload()
    ...     lot_w_package.quantity
    ...     lot_w_package.number_of_packages
    80.0
    0
    207.0
    51
    30.0
    6
    89.3
    19
    30.0
    6
    89.3
    19

Sale products::

    >>> Sale = Model.get('sale.sale')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.date = last_month + relativedelta(days=18)
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'manual'
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_wo_package
    >>> sale_line.quantity = 40.0
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_w_package
    >>> sale_line.quantity = 32.0

..     >>> sale_line.number_of_packages = 8

    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_lot_wo_package
    >>> sale_line.quantity = 10.0
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_lot_w_package
    >>> sale_line.quantity = 81.0

..     >>> sale_line.number_of_packages = 18

    >>> sale.save()
    >>> Sale.quote([sale.id], config.context)
    >>> Sale.confirm([sale.id], config.context)
    >>> Sale.process([sale.id], config.context)
    >>> sale.state
    u'processing'
    >>> sale.reload()
    >>> len(sale.shipments), len(sale.shipment_returns), len(sale.moves)
    (1, 0, 4)

..     >>> for move in sale.moves:
..     ...     if move.product in (product_wo_package, product_lot_wo_package):
..     ...         move.number_of_packages == None
..     ...     elif move.product == product_w_package:
..     ...         move.number_of_packages == 8
..     ...     elif move.product == product_lot_w_package:
..     ...         move.number_of_packages == 18
..     True
..     True
..     True
..     True

Check sale shpiment inventory moves::

    >>> shipment_out, = sale.shipments
    >>> len(shipment_out.inventory_moves)
    4

    >>> move_by_product = {m.product.id: m for m in shipment_out.inventory_moves}
    >>> move = move_by_product[product_wo_package.id]
    >>> move.number_of_packages

    >>> move = move_by_product[product_w_package.id]
    >>> move.number_of_packages
    >>> move.package = product_w_package.template.default_package
    >>> move.number_of_packages = 6
    >>> move.quantity
    24.0

    >>> move = move_by_product[product_lot_wo_package.id]
    >>> move.number_of_packages
    >>> move.lot = lot_wo_package
    >>> move.number_of_packages = 2

    >>> move = move_by_product[product_lot_w_package.id]
    >>> move.number_of_packages
    >>> move.lot = lot_w_package
    >>> move.number_of_packages = 18
    >>> move.quantity = round(move.quantity, 1)
    >>> round(move.quantity, 1)
    84.6

    >>> shipment_out.save()

Assign sale shipment::

    >>> shipment_out.click('assign_try')
    True

Check available quantities and forecast quantities::

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
    ...     product_lot_wo_package.reload()
    ...     product_lot_wo_package.quantity
    ...     product_lot_wo_package.number_of_packages
    ...     product_lot_wo_package.forecast_quantity
    ...     product_lot_wo_package.forecast_number_of_packages
    ...     product_lot_w_package.reload()
    ...     product_lot_w_package.quantity
    ...     product_lot_w_package.number_of_packages
    ...     product_lot_w_package.forecast_quantity
    ...     product_lot_w_package.forecast_number_of_packages
    ...     lot_wo_package.reload()
    ...     lot_wo_package.quantity
    ...     lot_wo_package.number_of_packages
    ...     lot_wo_package.forecast_quantity
    ...     lot_wo_package.forecast_number_of_packages
    ...     lot_w_package.reload()
    ...     lot_w_package.quantity
    ...     lot_w_package.number_of_packages
    ...     lot_w_package.forecast_quantity
    ...     lot_w_package.forecast_number_of_packages
    80.0
    0
    40.0
    0
    207.0
    51
    183.0
    45
    30.0
    6
    20.0
    4
    89.3
    19
    4.7
    1
    30.0
    6
    20.0
    4
    89.3
    19
    4.7
    1

Finalize the shipment::

    >>> shipment_out.reload()
    >>> shipment_out.click('pack') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserWarning: ...
    >>> shipment_out.reload()

Add origin to all moves::

    >>> origin = {l.product.id: l for l in sale.lines}
    >>> for move in shipment_out.moves:
    ...     move.origin = origin[move.product.id]
    >>> shipment_out.save()

Finalize the shipment::

    >>> shipment_out.reload()
    >>> shipment_out.click('pack')
    >>> shipment_out.reload()
    >>> shipment_out.click('done')

Create return sale::

    >>> return_sale = Wizard('sale.return_sale', [sale])
    >>> return_sale.execute('return_')
    >>> returned_sale, = Sale.find([
    ...     ('state', '=', 'draft'),
    ...     ])

..     >>> sorted([(x.quantity, x.number_of_packages) for x in returned_sale.lines])
..     [(-80.0, -4.0), (-40.0, None), (-30.0, -2.0), (-10.0, None)]

    >>> sorted([x.quantity for x in returned_sale.lines])
    [-81.0, -40.0, -32.0, -10.0]
    >>> for sale_line in returned_sale.lines:
    ...     if sale_line.product == product_wo_package:
    ...         sale_line.quantity = -25
    ...     elif sale_line.product == product_w_package:
    ...         sale_line.quantity = -12
    ...     elif sale_line.product == product_lot_wo_package:
    ...         sale_line.quantity = -5
    ...     elif sale_line.product == product_lot_w_package:
    ...         sale_line.quantity = -14.1
    >>> returned_sale.save()
    >>> returned_sale.click('quote')
    >>> returned_sale.click('confirm')
    >>> returned_sale.click('process')
    >>> returned_sale.state
    u'processing'
    >>> len(returned_sale.shipments), len(returned_sale.shipment_returns)
    (0, 1)

Validate return shipment::

    >>> shipment_return, = returned_sale.shipment_returns
    >>> moves_by_products = {m.product.id: m
    ...     for m in shipment_return.incoming_moves}
    >>> moves_by_products[product_wo_package.id].number_of_packages
    >>> moves_by_products[product_w_package.id].package \
    ...     = product_w_package.template.default_package
    >>> moves_by_products[product_w_package.id].number_of_packages = 3

    >>> moves_by_products[product_lot_wo_package.id].package
    >>> moves_by_products[product_lot_wo_package.id].lot = lot_wo_package
    >>> moves_by_products[product_lot_wo_package.id].number_of_packages = 1

    >>> moves_by_products[product_lot_w_package.id].lot = lot_w_package
    >>> moves_by_products[product_lot_w_package.id].number_of_packages = 3
    >>> moves_by_products[product_lot_w_package.id].quantity = round(moves_by_products[product_lot_w_package.id].quantity, 1)

    >>> shipment_return.save()
    >>> shipment_return.click('receive')
    >>> shipment_return.click('done')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_package.reload()
    ...     product_wo_package.quantity
    ...     product_wo_package.number_of_packages
    ...     product_w_package.reload()
    ...     product_w_package.quantity
    ...     product_w_package.number_of_packages
    ...     product_lot_wo_package.reload()
    ...     product_lot_wo_package.quantity
    ...     product_lot_wo_package.number_of_packages
    ...     product_lot_w_package.reload()
    ...     product_lot_w_package.quantity
    ...     product_lot_w_package.number_of_packages
    ...     lot_wo_package.reload()
    ...     lot_wo_package.quantity
    ...     lot_wo_package.number_of_packages
    ...     lot_w_package.reload()
    ...     lot_w_package.quantity
    ...     lot_w_package.number_of_packages
    65.0
    0
    195.0
    48
    25.0
    5
    18.8
    4
    25.0
    5
    18.8
    4

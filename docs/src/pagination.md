# Pagination

A `paginated` decorator is provided to help when the same function should be called
several times, with each call returning a partial set of the data.

!!! Note

    This works for any functions and methods, not just for methods of `Client`
    subclasses.

## Overview

Your friend Ranis is a well-known wizard who has several spells for sale. She gives you
a function that returns the spells she's selling, given a budget. However, at most 3
items are returned at a time, so you have to call it multiple times to retrieve the list
of all her spells.

### By page index

Given the following `list_spells` function:

    :::python
    >>> list_spells(max_price=50, page=0)
    ['Crushing Burden Touch', 'Great Burden of Sin', 'Heavy Burden']

    >>> list_spells(max_price=50, page=1)
    ['Strong Feather', "Tinur's Hoptoad", "Ulms's Juicedaw's Feather"]

    >>> list_spells(max_price=50, page=2)
    ['Far Silence', 'Soul Trap']

    >>> list_spells(max_price=50, page=3)
    []

Use `pagination.page`:

    :::python
    >>> from sdkite import paginated

    >>> @paginated()
    ... def get_spells1(pagination, max_price):
    ...     return list_spells(max_price=max_price, page=pagination.page)

    >>> result = get_spells1(50)  # the only parameter of get_spells1 is max_price
    >>> isinstance(result, Iterator)
    True

    >>> for spell in result:
    ...     print(repr(spell))
    'Crushing Burden Touch'
    'Great Burden of Sin'
    'Heavy Burden'
    'Strong Feather'
    "Tinur's Hoptoad"
    "Ulms's Juicedaw's Feather"
    'Far Silence'
    'Soul Trap'

### By the position of the first item

Given the following `list_spells` function:

    :::python
    >>> list_spells(max_price=50, offset=0)
    ['Crushing Burden Touch', 'Great Burden of Sin', 'Heavy Burden']

    >>> list_spells(max_price=50, offset=1)  # overlap with last call
    ['Great Burden of Sin', 'Heavy Burden', 'Strong Feather']

Use `pagination.offset`:

    :::python
    >>> @paginated()
    ... def get_spells2(pagination, max_price):
    ...     return list_spells(max_price=max_price, offset=pagination.offset)

    >>> for spell in get_spells2(50):
    ...     print(repr(spell))
    'Crushing Burden Touch'
    'Great Burden of Sin'
    'Heavy Burden'
    'Strong Feather'
    "Tinur's Hoptoad"
    "Ulms's Juicedaw's Feather"
    'Far Silence'
    'Soul Trap'

### By the reference to the next page

To avoid having invalid results due to items changing between two calls, some APIs gives
you a reference to the next page of your query.

Given the following `list_spells_with_ref` function:

    :::python
    >>> list_spells_with_ref(max_price=50)
    (['Crushing Burden Touch', 'Great Burden of Sin', 'Heavy Burden'], '57656c636')

    >>> list_spells_with_ref(cursor="57656c636")
    (['Strong Feather', "Tinur's Hoptoad", "Ulms's Juicedaw's Feather"], 'f6d652074')

    >>> list_spells_with_ref(cursor="f6d652074")
    (['Far Silence', 'Soul Trap'], '6f2042616')

    >>> list_spells_with_ref(cursor="6f2042616")
    ([], 'c6d6f7261')

Use `pagination.context` to store this reference:

    :::python
    >>> @paginated()
    ... def get_spells3(pagination, max_price):
    ...     if pagination.context is None:
    ...         data, next_cursor = list_spells_with_ref(max_price=max_price)
    ...     else:
    ...         data, next_cursor = list_spells_with_ref(cursor=pagination.context)
    ...     pagination.context = next_cursor
    ...     return data

    >>> for spell in get_spells3(50):
    ...     print(repr(spell))
    'Crushing Burden Touch'
    'Great Burden of Sin'
    'Heavy Burden'
    'Strong Feather'
    "Tinur's Hoptoad"
    "Ulms's Juicedaw's Feather"
    'Far Silence'
    'Soul Trap'

## Usage

### Decorated function

The decorated function must take `pagination` as its first parameter, which will be
inserted by the decorator with a `Pagination` instance.

!!! Note

    For methods of a class, the `pagination` parameter must come just after `self`.

An iterable must be returned by the decorated function. Items of this iterable will be
consumed one by one only when needed.

!!! Note

    The returned iterable can be of any size, which can vary at each call. However, if
    the iterable is empty, it will be assumed that the current page is the last, unless
    `stop_when_empty=False` was passed to `paginated`.

### The `Pagination` object

The following attributes of `pagination` are available:

`page` (read-only)

: The index of the current page.

`offset` (read-only)

: The index of the next item.

`context`

: Any arbitrary data that can be set on the `pagination` variable to persist from one
call of the decorated function to the other.

`finished` (read-only)

: A boolean indicating if a new page is expected to come after the current one.

`finish()`

: Call this method to indicate that the current page is the last one.

### The `paginated` decorator

The following parameters can be passed to `paginated`:

`page`, `offset`, `context`

: The initial values of the corresponding attributes of the `Pagination` object passed
to the decorated function (default to `0`, `0` and `None` respectively).

`stop_when_empty`

: Whether a next page will be fetched if no items have been generated on the current
page (defaults to `True`). If `False`, the `finish` method of the `Pagination` object
must me called to tell when to stop.

from random import uniform
from math import floor

from nose.tools import *

import one_commodity


"""
one_commodity.py
"""


def test_first_purchase_desired_matches_demand_curve():
    consumer = one_commodity.Consumer(10, 1)
    for price in range(11):
        desired = consumer.desired_at_price(price)
        assert_equal(desired, 10 - price)


def test_first_purchase_random_demand_curve():
    for _ in range(100):
        max_for_free = uniform(1, 10)
        less_per_dollar = uniform(.1, max_for_free)
        for price in range(1, 10):
            c = one_commodity.Consumer(max_for_free, less_per_dollar)
            expected = max(max_for_free - price * less_per_dollar, 0)
            desired = c.desired_at_price(price)
            assert_equal(expected, desired)


def test_second_purchase():
    """After purchasing 2 at one price, how many are desired at a new price?"""
    max_for_free = 20
    less_per_dollar = 1
    for first_price in range(1, 9):
        for second_price in range(first_price + 1, 15):
            c = one_commodity.Consumer(max_for_free, less_per_dollar)
            c.purchase(2, first_price)

            desired_at_second_price = c.desired_at_price(second_price)

            total_desired = 2 + desired_at_second_price
            average_price = (
                2 * first_price +
                desired_at_second_price * second_price
            ) / (2 + desired_at_second_price)

            correct_desired = max_for_free - less_per_dollar * average_price
            assert_almost_equal(correct_desired, total_desired)

            c.reset()
            assert_almost_equal(
                c.desired_at_price(average_price),
                total_desired)

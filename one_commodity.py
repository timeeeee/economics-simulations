"""
Simple supply/demand simulation with 1 good

In each round, a producer produces some amount of a good, and sets a price.

Consumers make purchases from the consumers. The consumers go in a random
order, but always purchase from the producer with the lowest price who still
has something in stock. When all of the producers are out of stock, or no
consumers want to buy, purchasing ends.

After the purchasing round, all producers update their estimate of the current
price.



Each consumer has a demand curve indicating how much of the good they will buy
at a particular price. Consumers, in a random order, purchase an amount of the
good from the producer with the lowest price, according to their demand curve.
If the producer runs out of the good, the consumer purchases from the producer
with the next lowest price, as long as the average price they've paid and the
total amount they've purchased are within their demand curve.

At the end of the round, each producer must adjust their price. If they sold
all of their goods, they raise the price by some amount. If they did not sell
all of their goods, they lower it by some amount.

Questions:
- How much oscillation will their be? Will the producers converge on a
  reasonable price?
- Can the behavior of the producers be described by a supply curve? I should
  look up: how does the amount supplied move up and down along a supply curve?
- Is the average price over time equivalent to the intersection of the market
  supply and demand curves?
- Is chaotic/periodic oscillation in the prices dampened by variation in the
  invidual supply/demand curves?
- Is chaotic/periodic oscillation in prices aggravated by an estimate of the
  "velocity" of the price?
- Is oscillation dampened by using a PID filter to guess the price?
"""

from random import random, shuffle
from math import sqrt

PRICE_ADJUSTMENT = 1.02
NEXT_PRODUCER_ID = 0
NEXT_CONSUMER_ID = 0


class Producer(object):
    """
    Produce and sell a commodity on a market. Use a supply curve to determine
    how much to produce. Maintain a price belief, adjusted up or down based on
    whether or not the stock sold out in the previous round.

    The supply curve will be based on a minimum price at which the producer
    starts to produce (really, where the production goes from negative to 0)
    and a "more per dollar" amount, so at a particular price they wil produce
    (price - minimum_price) * more_per_dollar

    OR MAYBE INSTEAD
    amount_for_free + more_per_dollar * price, which will be NEGATIVE until
    the price hits the minimum price?
    """
    def __init__(self, minimum_price, more_per_dollar, price_belief):
        self.stock = 0
        self.price = price_belief

        self.minimum_price = minimum_price
        self.more_per_dollar = more_per_dollar

        global NEXT_PRODUCER_ID
        self.producer_id = NEXT_PRODUCER_ID
        NEXT_PRODUCER_ID += 1

    def produce(self):
        """Produce some amount of a good."""
        self.stock = max(
            0,
            (self.price - self.minimum_price) * self.more_per_dollar)

    def sell(self, max_amount):
        """
        Sell all stock, or max_amount, whichever is smaller. Return the amount
        sold.
        """
        sold = min(max_amount, self.stock)
        self.stock -= sold
        return sold

    def adjust_price(self):
        """
        If all goods were sold in the last round, increase the price a little
        bit. Otherwise, decrease it a little bit, but not below the production
        cost.
        """
        if self.stock == 0:
            self.price *= PRICE_ADJUSTMENT
        else:
            self.price = self.price / PRICE_ADJUSTMENT


class Consumer(object):
    """
    A consumer purchases a good from producers according to its (linear) demand
    curve.
    """
    def __init__(self, amount_for_free, less_per_dollar):
        """
        The demand curve will be
        desired = amount_for_free - less_per_dollar * price
        """
        self.amount_for_free = amount_for_free
        self.less_per_dollar = less_per_dollar

        # Keep track of purchases per round
        self.purchased_this_round = 0
        self.paid_this_round = 0

        global NEXT_CONSUMER_ID
        self.consumer_id = NEXT_CONSUMER_ID
        NEXT_CONSUMER_ID += 1

    def reset(self):
        """Reset counts for the start of a round"""
        self.purchased_this_round = 0
        self.paid_this_round = 0

    def desired_at_price(self, price):
        """
        Given that the consumer has already purchased some amount of this good
        this round (self.purchased_this_round) for a certain amound of money
        (self.paid_this_round), how much more can we buy at a given price,
        without the total amount purchased exceeding the demand curve for the
        average price? (bleah)

        f = "amount for free
        l = "less per dollar"
        r = "price"
        ... so the demand curve is f - l * r
        p = "paid so far"
        s = "amount purchased so far"
        d = desired

        After buying the additional desired commodities
        purchaser has paid p + r * d
        total amount purchased is s + d
        new average price is (p + r * d) / (s + d)
        What is d to make these match the demand curve?

        s + d = f - l * (p + r * d) / (s + d)
        (s + d)(s + d) = f(s + d) - lp - lrd
        s**2 + 2sd + d**2 = fs + fd - lp - lrd
        d**2 + (2s + lr - f) d + (s**2 - fs + lp) = 0

        so for quadratic equation (-b +/- sqrt(b**2 - 4ac)) / 2a,
        a = 1
        b = 2 * s + l * r - f
        c = s**2 + l * p - f * s

        since a is always 1 the possible solutions are
        (-b + sqrt(b**2 - 4 * c)) / 2
        (-b - sqrt(b**2 - 4 * c)) / 2

        I hope that there will never be two positive solutions! I'll assert the
        smaller solution is negative, and take the larger for the answer.
        """
        b = (
            2 * self.purchased_this_round +
            self.less_per_dollar * price -
            self.amount_for_free)
        c = (
            self.purchased_this_round**2 +
            self.less_per_dollar * self.paid_this_round -
            self.amount_for_free * self.purchased_this_round)

        sqrt_part = sqrt(b**2 - 4 * c)

        # print((-b - sqrt_part) / 2, (-b + sqrt_part) / 2)

        # If the smaller solution is negative I'll have to figure out why
        assert (-b - sqrt_part) <= 0

        desired = (-b + sqrt_part) / 2
        return max(desired, 0)

    def purchase(self, amount, price):
        """
        Add a purchase to this round.
        """
        self.purchased_this_round += amount
        self.paid_this_round += price * amount


def simulate_round(producers, consumers):
    """
    Producers produce some amount of a commodity based on their current price
    belief.

    Consumers, in random order, purchase from producers in order by price,
    until they hit their demand curve.

    They round is over when either all of the producers are out of stock, or
    none of the consumers want to make any more purchases.

    After the round, each producer adjusts their price belief- if they have
    stock left over, they lower their price, and if they sold out, they raise
    their price.

    Return (amount sold, average price)
    """
    # Producers make some stuff
    for producer in producers:
        producer.produce()

    # Reset consumer paid/purchased counts for round
    for consumer in consumers:
        consumer.reset()

    # producers go in order by price ascending
    producer_queue = list(producers)
    producer_queue.sort(key=lambda p: p.price)

    # consumers go in random order
    consumer_queue = list(consumers)
    shuffle(consumer_queue)

    total_sold = 0
    total_paid = 0

    consumer = consumer_queue.pop(0)
    producer = producer_queue.pop(0)
    while producer_queue and consumer_queue:
        # Make a transaction
        desired = int(consumer.desired_at_price(producer.price))
        purchased = producer.sell(desired)
        consumer.purchase(purchased, producer.price)

        # print("consumer {} purchasing {} from producer {} at {}".format(
        #     consumer.consumer_id, purchased, producer.producer_id,
        #     producer.price))

        total_sold += purchased
        total_paid += purchased * producer.price

        if producer.stock == 0:
            # print("producer {} out of stock".format(producer.producer_id))
            producer = producer_queue.pop(0)

        if desired == purchased:
            # print("consumer {} done purchasing".format(consumer.consumer_id))
            consumer = consumer_queue.pop(0)
        else:
            # Otherwise, we need to choose a new random consumer
            shuffle(consumer_queue)

    # Now all producers adjust their price based on whether they're sold out
    for producer in producers:
        producer.adjust_price()

    return (total_sold, total_paid / total_sold)


if __name__ == "__main__":
    producers = [Producer(1, 1, 6 + 2 * i) for i in range(10)]
    consumers = [Consumer(20, 1) for _ in range(10)]

    for round_num in range(100):
        prices = [p.price for p in producers]
        average = sum(prices) / 10
        # print(",".join(str(p) for p in (prices + [average])))
        total_sold, average_price = simulate_round(producers, consumers)
        print("{},{}".format(total_sold, average_price))

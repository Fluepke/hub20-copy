import factory

from hub20.apps.core import models
from hub20.apps.ethereum_money.factories import UserTokenListFactory

from .base import UserFactory
from .payments import Erc20TokenPaymentOrderFactory


class StoreFactory(factory.django.DjangoModelFactory):
    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Store #{n:02}")
    url = factory.Sequence(lambda n: f"https://store-{n:02}.example.com")
    accepted_token_list = factory.SubFactory(
        UserTokenListFactory, user=factory.SelfAttribute("..owner")
    )
    checkout_webhook_url = factory.Sequence(lambda n: f"https://store#{n:02}.example.com/checkout")

    class Meta:
        model = models.Store


class CheckoutFactory(factory.django.DjangoModelFactory):
    store = factory.SubFactory(StoreFactory, accepted_token_list__tokens=[])
    order = factory.SubFactory(
        Erc20TokenPaymentOrderFactory,
        user=factory.SelfAttribute("..store.owner"),
        reference=factory.fuzzy.FuzzyText(length=30, prefix="checkout-"),
    )

    class Meta:
        model = models.Checkout


__all__ = ["StoreFactory", "CheckoutFactory"]

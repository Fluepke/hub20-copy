from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views
from .consumers import CheckoutConsumer, SessionEventsConsumer

app_name = "hub20"


router = SimpleRouter(trailing_slash=False)
router.register("checkout", views.CheckoutViewSet, basename="checkout")
router.register("payments", views.PaymentViewSet, basename="payments")
router.register("stores", views.StoreViewSet, basename="store")
router.register("users", views.UserViewSet, basename="users")


urlpatterns = [
    path("credits", views.AccountCreditEntryList.as_view(), name="credit-list"),
    path("debits", views.AccountDebitEntryList.as_view(), name="debit-list"),
    path("balances", views.TokenBalanceListView.as_view(), name="balance-list"),
    path("balance/<str:address>", views.TokenBalanceView.as_view(), name="balance-detail"),
    path("deposits", views.DepositListView.as_view(), name="deposit-list"),
    path("deposit/<uuid:pk>", views.DepositView.as_view(), name="deposit-detail"),
    path("payment/orders", views.PaymentOrderListView.as_view(), name="payment-order-list"),
    path("payment/order/<uuid:pk>", views.PaymentOrderView.as_view(), name="payment-order-detail"),
    path("transfers", views.TransferListView.as_view(), name="transfer-list"),
    path("transfers/transfer/<int:pk>", views.TransferView.as_view(), name="transfer-detail"),
    path("status/networks", views.NetworkStatusListView.as_view(), name="status-network-list"),
    path(
        "status/networks/<int:pk>",
        views.NetworkStatusDetailView.as_view(),
        name="status-network-detail",
    ),
    path("status/accounting", views.AccountingReportView.as_view(), name="status-accounting"),
    path(
        "status/accounts",
        views.EthereumAccountBalanceSheets.as_view(),
        name="status-accounts",
    ),
] + router.urls


consumer_patterns = [
    path("events", SessionEventsConsumer.as_asgi()),
    path("checkout/<uuid:pk>", CheckoutConsumer.as_asgi()),
]

from django_celery_results.models import TaskResult
from raiden_contracts.contract_manager import gas_measurements
from rest_framework import serializers
from rest_framework_nested.relations import (
    NestedHyperlinkedIdentityField,
    NestedHyperlinkedRelatedField,
)
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer

from hub20.apps.blockchain.client import make_web3
from hub20.apps.blockchain.models import Web3Provider
from hub20.apps.blockchain.serializers import HexadecimalField
from hub20.apps.ethereum_money.client import get_account_balance
from hub20.apps.ethereum_money.models import EthereumTokenAmount
from hub20.apps.ethereum_money.serializers import (
    EthereumTokenSerializer,
    HyperlinkedEthereumTokenSerializer,
    TokenValueField,
)
from hub20.apps.ethereum_money.typing import TokenAmount

from . import models
from .client.blockchain import get_service_token, get_service_token_contract
from .client.node import RaidenClient
from .tasks import make_udc_deposit


class ChainField(serializers.PrimaryKeyRelatedField):
    queryset = models.Chain.objects.filter(tokens__tokennetwork__isnull=False).distinct()


class TokenNetworkField(serializers.RelatedField):
    queryset = models.TokenNetwork.objects.all()
    lookup_field = "address"


class TokenNetworkSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="token-network-detail", lookup_field="address"
    )
    token = HyperlinkedEthereumTokenSerializer()

    class Meta:
        model = models.TokenNetwork
        fields = ("url", "address", "token")
        read_only_fields = ("url", "address", "token")


class ManagementTaskSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="task_name")
    created = serializers.DateTimeField(source="date_created")
    completed = serializers.DateTimeField(source="date_done")

    class Meta:
        model = TaskResult
        fields = read_only_fields = ("name", "status", "created", "completed")


class ManagementOrderSerializer(serializers.ModelSerializer):
    raiden = serializers.HyperlinkedRelatedField(
        view_name="raiden-detail", queryset=models.Raiden.objects.all()
    )

    class Meta:
        model = models.RaidenManagementOrder
        fields = ("raiden", "task_result")
        read_only_fields = "task_result"


class ServiceDepositSerializer(serializers.ModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name="service-deposit-detail",
        parent_lookup_kwargs={
            "raiden_pk": "raiden_id",
        },
    )
    raiden = serializers.HyperlinkedRelatedField(
        view_name="raiden-detail", queryset=models.Raiden.objects.all()
    )
    amount = TokenValueField()
    result = ManagementTaskSerializer(source="task_result", read_only=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Need to deposit a value larger than 0")

        return value

    def validate(self, data):
        raiden = data["raiden"]

        if self.Meta.model.objects.filter(raiden=raiden, task_result__status="PENDING").exists():
            raise serializers.ValidationError("Another similar operation is pending execution")

        w3 = make_web3(provider=raiden.chain.provider)
        token = get_service_token(w3=w3)

        deposit_amount = EthereumTokenAmount(currency=token, amount=data["amount"])
        balance = get_account_balance(w3=w3, token=token, address=raiden.address)

        if balance < deposit_amount:
            raise serializers.ValidationError(f"Insufficient balance: {balance}")

        return data

    def create(self, validated_data):
        raiden = validated_data["raiden"]
        amount = validated_data["amount"]

        w3 = make_web3(provider=raiden.chain.provider)
        service_token = get_service_token(w3=w3)

        task = make_udc_deposit.delay(raiden_url=raiden.url, amount=amount)
        result = TaskResult.objects.get_task(task.id)
        result.save()

        return self.Meta.model.objects.create(
            raiden=raiden, amount=amount, currency=service_token, task_result=result
        )

    class Meta:
        model = models.UserDepositContractOrder
        fields = ("url", "created", "raiden", "amount", "result")
        read_only_fields = ("url", "created", "result")


class ChannelSerializer(NestedHyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name="raiden-channel-detail",
        parent_lookup_kwargs={
            "raiden_pk": "raiden_id",
        },
    )
    token = HyperlinkedEthereumTokenSerializer(source="token_network.token", read_only=True)

    class Meta:
        model = models.Channel
        fields = ("url", "id", "token", "identifier", "partner_address", "status", "balance")
        read_only_fields = (
            "url",
            "id",
            "token",
            "identifier",
            "partner_address",
            "status",
            "balance",
        )


class ChannelManagementSerializer(NestedHyperlinkedModelSerializer):
    parent_lookup_kwargs = {"raiden_pk": "channel__raiden_id", "channel_pk": "channel_id"}

    channel = NestedHyperlinkedRelatedField(
        view_name="raiden-channel-detail",
        parent_lookup_kwargs={"raiden_pk": "raiden_id"},
        read_only=True,
    )
    amount = TokenValueField()

    def validate(self, data):
        channel = self.get_channel()
        if channel is None:
            raise serializers.ValidationError("Can not get channel information")
        data["channel"] = channel
        return data

    def create(self, validated_data):
        channel = validated_data.pop("channel")
        request = self.context["request"]

        return self.Meta.model.objects.create(
            raiden=channel.raiden, channel=channel, user=request.user, **validated_data
        )

    def get_channel(self):
        view = self.context["view"]

        return models.Channel.objects.filter(
            raiden_id=view.kwargs["raiden_pk"], pk=view.kwargs["channel_pk"]
        ).first()


class ChannelDepositSerializer(ChannelManagementSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name="raiden-channel-deposit-detail",
        parent_lookup_kwargs={"raiden_pk": "channel__raiden_id", "channel_pk": "channel_id"},
    )

    def create(self, validated_data):
        breakpoint()

    class Meta:
        model = models.ChannelDepositOrder
        fields = ("url", "id", "created", "channel", "amount")
        read_only_fields = ("url", "id", "created", "channel")


class ChannelWithdrawalSerializer(ChannelManagementSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name="raiden-channel-withdrawal-detail",
        parent_lookup_kwargs={"raiden_pk": "channel__raiden_id", "channel_pk": "channel_id"},
    )

    class Meta:
        model = models.ChannelWithdrawOrder
        fields = ("url", "id", "created", "channel", "amount")
        read_only_fields = ("url", "id", "created", "channel")

    def validate_amount(self, data):
        channel = self.get_channel()
        if channel is None:
            raise serializers.ValidationError("Can not get channel information")

        token = channel.token
        amount = TokenAmount(data).normalize()
        withdraw_amount = EthereumTokenAmount(amount=amount, currency=token)
        channel_balance = EthereumTokenAmount(amount=channel.balance, currency=token)

        if withdraw_amount > channel_balance:
            raise serializers.ValidationError(f"Insufficient balance: {channel_balance.formatted}")

        return data


class RaidenSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="raiden-detail")
    chain = serializers.HyperlinkedRelatedField(
        view_name="blockchain:chain-detail", read_only=True
    )
    channels = ChannelSerializer(many=True)
    status = serializers.HyperlinkedIdentityField(view_name="raiden-status")

    class Meta:
        model = models.Raiden
        fields = read_only_fields = ("url", "id", "status", "chain", "address", "channels")


class RaidenStatusSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="raiden-status")
    raiden = serializers.HyperlinkedIdentityField(view_name="raiden-detail")
    online = serializers.SerializerMethodField()
    cost_estimates = serializers.SerializerMethodField()

    def get_online(self, obj):
        client = RaidenClient(raiden_node=obj)
        return "ready" == client.get_status()

    def get_cost_estimates(self, obj):
        try:
            provider = Web3Provider.active.get(chain_id=obj.chain.id)
            w3 = make_web3(provider=provider)
            gas_price = w3.eth.generate_gas_price()
            gas_costs = gas_measurements()
            actions = {
                "udc-deposit": gas_costs["UserDeposit.deposit"],
                "udc-topup": gas_costs["UserDeposit.deposit (increase balance)"],
                "udc-withdraw": (
                    gas_costs["UserDeposit.planWithdraw"] + gas_costs["UserDeposit.withdraw"]
                ),
                "channel-setup": gas_costs["TokenNetwork.openChannelWithDeposit"],
                "channel-open": gas_costs["TokenNetwork.openChannel"],
                "channel-deposit": gas_costs["TokenNetwork.setTotalDeposit"],
                "channel-withdraw": gas_costs["TokenNetwork.setTotalWithdraw"],
                "channel-close": gas_costs["TokenNetwork.closeChannel"],
            }
            return {k: gas_price and (v * gas_price) for k, v in actions.items()}
        except Web3Provider.DoesNotExist:
            return None

    class Meta:
        model = models.Raiden
        fields = read_only_fields = ("url", "raiden", "online", "cost_estimates")


class JoinTokenNetworkOrderSerializer(serializers.ModelSerializer):
    token_network = serializers.HyperlinkedRelatedField(
        view_name="token-network-detail", lookup_field="address", read_only=True
    )

    def get_token_network(self):
        view = self.context.get("view")
        return view and view.get_object()

    def create(self, validated_data):
        request = self.context["request"]
        token_network = self.get_token_network()

        return self.Meta.model.objects.create(
            raiden=self.raiden, token_network=token_network, user=request.user, **validated_data
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        token_network = self.get_token_network()

        assert isinstance(self.raiden, models.Raiden)
        if token_network in self.raiden.token_networks:
            raise serializers.ValidationError(
                f"Already joined token network {token_network.address}"
            )

        return attrs

    class Meta:
        model = models.JoinTokenNetworkOrder
        fields = ("id", "created", "token_network", "amount")
        read_only_fields = ("id", "created", "token_network")

# inventory/api/serializers.py
from rest_framework import serializers
from .models import Inventory, Warehouse, StockReservation, StorageLocation


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    location_code = serializers.CharField(source='location.code', read_only=True, allow_null=True)
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'warehouse', 'warehouse_name', 'location', 'location_code',
            'quantity', 'reserved_quantity', 'available_quantity',
            'batch_number', 'unit_cost', 'total_value', 'status',
            'manufacturing_date', 'expiry_date', 'last_updated'
        ]
        read_only_fields = ['available_quantity', 'total_value']


class WarehouseSerializer(serializers.ModelSerializer):
    capacity_percentage = serializers.FloatField(read_only=True)
    available_capacity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    manager_name = serializers.CharField(source='manager.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Warehouse
        fields = [
            'id', 'code', 'name', 'location',
            'contact_person', 'phone', 'email', 'address',
            'total_capacity', 'used_capacity', 'available_capacity', 'capacity_percentage',
            'is_active', 'warehouse_type', 'manager', 'manager_name',
            'created_at', 'updated_at'
        ]


class StorageLocationSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    available_volume = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_weight = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = StorageLocation
        fields = [
            'id', 'warehouse', 'warehouse_name', 'warehouse_code',
            'code', 'name', 'location_type',
            'aisle', 'section', 'shelf', 'level', 'position',
            'max_volume', 'max_weight', 'current_volume', 'current_weight',
            'available_volume', 'available_weight',
            'is_active', 'is_full',
            'created_at', 'updated_at'
        ]


class StockReservationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True, allow_null=True)
    customer_name = serializers.CharField(source='customer.user.username', read_only=True, allow_null=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = StockReservation
        fields = [
            'id', 'reservation_number', 'product', 'product_name', 'product_sku',
            'order', 'order_number', 'customer', 'customer_name',
            'quantity', 'backorder_quantity', 'status',
            'expires_at', 'is_expired',
            'reserved_at', 'allocated_at', 'released_at',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['reservation_number', 'reserved_at', 'allocated_at', 'released_at']


# 请求序列化器
class StockCheckSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)


class StockReserveSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    order_id = serializers.UUIDField(required=False, allow_null=True)
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)
    expires_in_hours = serializers.IntegerField(min_value=1, max_value=168, default=24)  # 最多7天


class StockReleaseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)


class StockAllocateSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=200, required=False, allow_blank=True)


class StockReceiveSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    warehouse_id = serializers.UUIDField(required=True)
    batch_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    location_id = serializers.UUIDField(required=False, allow_null=True)
# inventory/api/filters.py
import django_filters as filters
from .models import Inventory, Warehouse, StockReservation


class InventoryFilter(filters.FilterSet):
    product = filters.UUIDFilter(field_name='product__id')
    product_sku = filters.CharFilter(field_name='product__sku')
    product_name = filters.CharFilter(field_name='product__name', lookup_expr='icontains')
    warehouse = filters.UUIDFilter(field_name='warehouse__id')
    warehouse_code = filters.CharFilter(field_name='warehouse__code')
    status = filters.ChoiceFilter(choices=Inventory.STATUS_CHOICES)
    available_quantity_min = filters.NumberFilter(field_name='available_quantity', lookup_expr='gte')
    available_quantity_max = filters.NumberFilter(field_name='available_quantity', lookup_expr='lte')
    expiry_date_min = filters.DateFilter(field_name='expiry_date', lookup_expr='gte')
    expiry_date_max = filters.DateFilter(field_name='expiry_date', lookup_expr='lte')
    
    class Meta:
        model = Inventory
        fields = [
            'product', 'product_sku', 'product_name',
            'warehouse', 'warehouse_code',
            'status', 'available_quantity_min', 'available_quantity_max',
            'expiry_date_min', 'expiry_date_max'
        ]


class WarehouseFilter(filters.FilterSet):
    code = filters.CharFilter(lookup_expr='icontains')
    name = filters.CharFilter(lookup_expr='icontains')
    location = filters.CharFilter(lookup_expr='icontains')
    warehouse_type = filters.ChoiceFilter(choices=Warehouse.WAREHOUSE_TYPES)
    is_active = filters.BooleanFilter()
    capacity_min = filters.NumberFilter(field_name='total_capacity', lookup_expr='gte')
    capacity_max = filters.NumberFilter(field_name='total_capacity', lookup_expr='lte')
    
    class Meta:
        model = Warehouse
        fields = [
            'code', 'name', 'location', 'warehouse_type',
            'is_active', 'capacity_min', 'capacity_max'
        ]


class StockReservationFilter(filters.FilterSet):
    product = filters.UUIDFilter(field_name='product__id')
    order = filters.UUIDFilter(field_name='order__id')
    customer = filters.UUIDFilter(field_name='customer__id')
    status = filters.ChoiceFilter(choices=StockReservation.RESERVATION_STATUS)
    reservation_number = filters.CharFilter(lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = StockReservation
        fields = [
            'product', 'order', 'customer',
            'status', 'reservation_number',
            'created_after', 'created_before'
        ]
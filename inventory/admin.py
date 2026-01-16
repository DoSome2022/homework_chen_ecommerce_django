# inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Warehouse, StorageLocation, Inventory, 
    StockReservation, ReservationAllocation,
    StockTransfer, TransferItem,
    StockAdjustment, AdjustmentItem
)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'location', 'warehouse_type', 
                   'total_capacity', 'used_capacity', 'capacity_percentage_display', 'is_active')
    list_filter = ('warehouse_type', 'is_active')
    search_fields = ('code', 'name', 'location')
    readonly_fields = ('available_capacity', 'capacity_percentage')
    
    def capacity_percentage_display(self, obj):
        return format_html(
            '<div style="width:100px; background:#ddd; border-radius:3px;">'
            '<div style="width:{}%; background:#4CAF50; height:20px; border-radius:3px; text-align:center; color:white; line-height:20px;">'
            '{}%</div></div>',
            obj.capacity_percentage, round(obj.capacity_percentage)
        )
    capacity_percentage_display.short_description = '占用率'


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'warehouse', 'location_type', 'aisle', 'shelf', 'level',
                   'max_volume', 'current_volume', 'available_volume_display', 'is_full', 'is_active')
    list_filter = ('warehouse', 'location_type', 'is_active', 'is_full')
    search_fields = ('code', 'name', 'aisle', 'shelf')
    readonly_fields = ('available_volume', 'available_weight')
    
    def available_volume_display(self, obj):
        return f'{obj.available_volume} m³'
    available_volume_display.short_description = '可用容量'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'reserved_quantity', 
                   'available_quantity', 'status', 'batch_number', 'expiry_date')
    list_filter = ('warehouse', 'status', 'product__category')
    search_fields = ('product__name', 'product__sku', 'batch_number')
    readonly_fields = ('available_quantity', 'total_value')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('product', 'warehouse', 'location')
        }),
        ('库存信息', {
            'fields': ('quantity', 'reserved_quantity', 'available_quantity', 
                      'batch_number', 'unit_cost', 'total_value')
        }),
        ('日期信息', {
            'fields': ('manufacturing_date', 'expiry_date')
        }),
        ('状态', {
            'fields': ('status', 'last_updated')
        })
    )


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_number', 'product', 'quantity', 'backorder_quantity',
                   'status', 'order', 'customer', 'reserved_at', 'expires_at_display')
    list_filter = ('status', 'product')
    search_fields = ('reservation_number', 'product__name', 'order__order_number')
    readonly_fields = ('reservation_number', 'reserved_at', 'allocated_at', 'released_at')
    
    def expires_at_display(self, obj):
        from django.utils import timezone
        if obj.expires_at:
            if obj.expires_at < timezone.now():
                return format_html('<span style="color:red;">已过期</span>')
            return obj.expires_at
        return '-'
    expires_at_display.short_description = '过期时间'


@admin.register(ReservationAllocation)
class ReservationAllocationAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'inventory', 'quantity', 'allocated_at')
    list_filter = ('reservation__status',)
    search_fields = ('reservation__reservation_number', 'inventory__product__name')


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'from_warehouse', 'to_warehouse', 
                   'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'from_warehouse', 'to_warehouse')
    search_fields = ('transfer_number', 'notes')
    readonly_fields = ('transfer_number', 'created_at', 'updated_at')


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('adjustment_number', 'warehouse', 'adjustment_type', 
                   'status', 'total_items', 'total_value_change', 'created_at')
    list_filter = ('adjustment_type', 'status', 'warehouse')
    search_fields = ('adjustment_number', 'reason')
    readonly_fields = ('adjustment_number', 'created_at', 'updated_at')
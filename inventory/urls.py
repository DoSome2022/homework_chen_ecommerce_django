# inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # API ViewSets
    InventoryViewSet, WarehouseViewSet,
    StockReservationViewSet, StorageLocationViewSet,
    
    # Web Views
    WarehouseListView, WarehouseDetailView,
    WarehouseCreateView, WarehouseUpdateView, WarehouseDeleteView,
    InventoryListView, InventoryDetailView,
    InventoryCreateView, InventoryUpdateView, InventoryDeleteView,
    TaskListView, QuickAddInventoryView,
    
    # AJAX Views
    add_form_field, get_product_by_sku, get_locations_by_warehouse
)

router = DefaultRouter()
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'stock-reservations', StockReservationViewSet, basename='stock-reservation')
router.register(r'storage-locations', StorageLocationViewSet, basename='storage-location')

app_name = 'inventory'

urlpatterns = [
    # 主页
    path('', WarehouseListView.as_view(), name='warehouse_list'),
    
    # 仓库管理
    path('warehouses/', WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouse/create/', WarehouseCreateView.as_view(), name='warehouse_create'),
    path('warehouse/<uuid:pk>/', WarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouse/<uuid:pk>/update/', WarehouseUpdateView.as_view(), name='warehouse_update'),
    path('warehouse/<uuid:pk>/delete/', WarehouseDeleteView.as_view(), name='warehouse_delete'),
    
    # 库存管理
    path('inventory/', InventoryListView.as_view(), name='inventory_list'),
    path('inventory/add/', InventoryCreateView.as_view(), name='inventory_create'),
    path('inventory/quick-add/', QuickAddInventoryView.as_view(), name='inventory_quick_add'),
    path('inventory/<uuid:pk>/', InventoryDetailView.as_view(), name='inventory_detail'),
    path('inventory/<uuid:pk>/update/', InventoryUpdateView.as_view(), name='inventory_update'),
    path('inventory/<uuid:pk>/delete/', InventoryDeleteView.as_view(), name='inventory_delete'),
    
    # 任务管理
    path('tasks/', TaskListView.as_view(), name='task_list'),
    
    # AJAX API
    path('add-form-field/', add_form_field, name='add_form_field'),
    path('api/get-product/', get_product_by_sku, name='get_product_by_sku'),
    path('api/get-locations/', get_locations_by_warehouse, name='get_locations_by_warehouse'),
    
    # REST API
    path('api/', include(router.urls)),
]
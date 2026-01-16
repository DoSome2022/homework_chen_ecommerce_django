# inventory/api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters import rest_framework as filters
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
import json

# 正确导入表单
from .forms import (
    WarehouseForm, WarehouseZoneForm, WarehouseAisleForm, 
    WarehouseShelfForm, WarehouseCreationFormSet,
    InventoryForm, InventorySearchForm, QuickAddInventoryForm
)

# 正确导入模型
from .models import (
    Warehouse, Inventory, WarehouseTask, WarehouseTransaction,
    StockReservation, StorageLocation, ReservationAllocation
)

# 导入服务和序列化器
from .services import InventoryService, WarehouseService
from .serializers import (
    InventorySerializer, WarehouseSerializer, 
    StockReservationSerializer, StorageLocationSerializer,
    StockCheckSerializer, StockReserveSerializer,
    StockReleaseSerializer, StockAllocateSerializer,
    StockReceiveSerializer
)
from .filters import InventoryFilter, WarehouseFilter, StockReservationFilter

logger = logging.getLogger(__name__)


class InventoryViewSet(viewsets.ModelViewSet):
    """库存API"""
    queryset = Inventory.objects.select_related('product', 'warehouse', 'location').all()
    serializer_class = InventorySerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = InventoryFilter
    
    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """检查库存可用性"""
        serializer = StockCheckSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            warehouse_id = serializer.validated_data.get('warehouse_id')
            
            is_available, message, inventories = InventoryService.check_product_availability(
                product_id, quantity, warehouse_id
            )
            
            return Response({
                'available': is_available,
                'message': message,
                'inventories': InventorySerializer(inventories, many=True).data if inventories else []
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取库存摘要"""
        warehouse_id = request.query_params.get('warehouse_id')
        product_id = request.query_params.get('product_id')
        
        summary = InventoryService.get_inventory_summary(warehouse_id, product_id)
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """获取低库存产品"""
        threshold = request.query_params.get('threshold', None)
        if threshold:
            try:
                threshold = int(threshold)
            except ValueError:
                threshold = None
        
        warehouse_id = request.query_params.get('warehouse_id')
        
        low_stock_items = InventoryService.get_low_stock_products(threshold, warehouse_id)
        
        page = self.paginate_queryset(low_stock_items)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)


class WarehouseViewSet(viewsets.ModelViewSet):
    """仓库API"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = WarehouseFilter
    
    @action(detail=True, methods=['get'])
    def capacity(self, request, pk=None):
        """获取仓库容量信息"""
        capacity_info = WarehouseService.get_warehouse_capacity(pk)
        if capacity_info:
            return Response(capacity_info)
        return Response({'error': '仓库不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def inventory(self, request, pk=None):
        """获取仓库库存"""
        warehouse = self.get_object()
        inventories = Inventory.objects.filter(warehouse=warehouse).select_related('product', 'location')
        
        page = self.paginate_queryset(inventories)
        if page is not None:
            serializer = InventorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = InventorySerializer(inventories, many=True)
        return Response(serializer.data)


class StockReservationViewSet(viewsets.ModelViewSet):
    """库存预留API"""
    queryset = StockReservation.objects.select_related('product', 'order', 'customer').all()
    serializer_class = StockReservationSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = StockReservationFilter
    
    @action(detail=False, methods=['post'])
    def reserve(self, request):
        """预留库存"""
        serializer = StockReserveSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            order_id = serializer.validated_data.get('order_id')
            customer_id = serializer.validated_data.get('customer_id')
            warehouse_id = serializer.validated_data.get('warehouse_id')
            
            success, message, reservation = InventoryService.reserve_stock(
                product_id, quantity, order_id, customer_id, warehouse_id
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': message,
                    'reservation': StockReservationSerializer(reservation).data
                })
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """释放库存"""
        serializer = StockReleaseSerializer(data=request.data)
        if serializer.is_valid():
            success, message = InventoryService.release_stock(pk)
            
            if success:
                return Response({
                    'success': True,
                    'message': message
                })
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        """分配库存"""
        serializer = StockAllocateSerializer(data=request.data)
        if serializer.is_valid():
            success, message = InventoryService.allocate_stock(pk)
            
            if success:
                return Response({
                    'success': True,
                    'message': message
                })
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StorageLocationViewSet(viewsets.ModelViewSet):
    """存储位置API"""
    queryset = StorageLocation.objects.select_related('warehouse').all()
    serializer_class = StorageLocationSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['post'])
    def receive_stock(self, request):
        """接收库存（入库）"""
        serializer = StockReceiveSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            warehouse_id = serializer.validated_data['warehouse_id']
            batch_number = serializer.validated_data.get('batch_number')
            unit_cost = serializer.validated_data.get('unit_cost')
            location_id = serializer.validated_data.get('location_id')
            
            success, message, inventory = WarehouseService.receive_stock(
                product_id, quantity, warehouse_id, batch_number, unit_cost, location_id
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': message,
                    'inventory': InventorySerializer(inventory).data
                })
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # 倉庫列表
class WarehouseListView(ListView):
    model = Warehouse
    template_name = 'inventory/warehouse_list.html'
    context_object_name = 'warehouses'

# 倉庫詳情
class WarehouseDetailView(DetailView):
    model = Warehouse
    template_name = 'inventory/warehouse_detail.html'
    context_object_name = 'warehouse'

# 庫存列表
class InventoryListView(ListView):
    model = Inventory
    template_name = 'inventory/inventory_list.html'
    context_object_name = 'inventories'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Inventory.objects.select_related(
            'product', 'warehouse', 'location'
        ).order_by('warehouse', 'product__name')
        
        # 应用搜索过滤器
        self.form = InventorySearchForm(self.request.GET)
        if self.form.is_valid():
            queryset = self.form.filter_queryset(queryset)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = self.form or InventorySearchForm()
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
        
        # 计算统计信息
        from django.db.models import Sum, Q
        
        # 使用当前的查询集计算统计
        queryset = self.get_queryset()
        
        # 总库存价值
        total_value = queryset.aggregate(total=Sum('total_value'))['total'] or 0
        context['total_value'] = total_value
        
        # 总库存数量
        total_quantity = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        context['total_quantity'] = total_quantity
        
        # 低库存产品数量
        low_stock_count = queryset.filter(
            available_quantity__lte=models.F('product__low_stock_threshold')
        ).count()
        context['low_stock_count'] = low_stock_count
        
        # 仓库数量
        warehouse_count = Warehouse.objects.filter(is_active=True).count()
        context['warehouse_count'] = warehouse_count
        
        return context

# 任務列表
class TaskListView(ListView):
    model = WarehouseTask
    template_name = 'inventory/task_list.html'
    context_object_name = 'tasks'
    queryset = WarehouseTask.objects.select_related('warehouse', 'assigned_to')


# 新增倉庫視圖
class WarehouseCreateView( CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'inventory/warehouse_create.html'
    success_url = reverse_lazy('inventory:warehouse_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zone_form'] = WarehouseZoneForm(prefix='zone_0')
        context['aisle_form'] = WarehouseAisleForm(prefix='aisle_0')
        context['shelf_form'] = WarehouseShelfForm(prefix='shelf_0')
        return context
    
    def form_valid(self, form):
        # 獲取額外的表單數據
        data = self.request.POST
        
        # 創建表單集
        formset = WarehouseCreationFormSet(data)
        
        if formset.is_valid():
            # 保存所有表單
            warehouse = formset.save(self.request.user)
            messages.success(self.request, f'倉庫 {warehouse.name} 創建成功！')
            return redirect(self.success_url)
        else:
            # 將錯誤返回給模板
            return self.render_to_response(self.get_context_data(
                form=form,
                zone_forms=formset.zone_forms,
                aisle_forms=formset.aisle_forms,
                shelf_forms=formset.shelf_forms,
            ))

# 更新倉庫視圖
class WarehouseUpdateView( UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'inventory/warehouse_update.html'
    
    def get_success_url(self):
        return reverse_lazy('inventory:warehouse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'倉庫 {self.object.name} 更新成功！')
        return super().form_valid(form)

# 刪除倉庫視圖
class WarehouseDeleteView( DeleteView):
    model = Warehouse
    template_name = 'inventory/warehouse_delete.html'
    success_url = reverse_lazy('inventory:warehouse_list')
    
    def delete(self, request, *args, **kwargs):
        warehouse = self.get_object()
        messages.success(request, f'倉庫 {warehouse.name} 刪除成功！')
        return super().delete(request, *args, **kwargs)

# API 視圖：動態添加表單
@csrf_exempt
def add_form_field(request):
    """動態添加表單字段"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            form_type = data.get('form_type')
            index = int(data.get('index', 0))
            
            if form_type == 'zone':
                form = WarehouseZoneForm(prefix=f'zone_{index}')
            elif form_type == 'aisle':
                form = WarehouseAisleForm(prefix=f'aisle_{index}')
            elif form_type == 'shelf':
                form = WarehouseShelfForm(prefix=f'shelf_{index}')
            else:
                return JsonResponse({'error': '無效的表單類型'}, status=400)
            
            # 渲染表單HTML
            html = form.as_table()
            return JsonResponse({'html': html, 'index': index})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': '僅接受POST請求'}, status=405)


class StaffRequiredMixin():
    """要求用户必须是员工"""
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff or 
            hasattr(self.request.user, 'staff_profile')
        )


class InventoryListView( ListView):
    """库存列表视图"""
    model = Inventory
    template_name = 'inventory/inventory_list.html'
    context_object_name = 'inventories'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Inventory.objects.select_related(
            'product', 'warehouse', 'location'
        ).order_by('warehouse', 'product__name')
        
        # 应用搜索过滤器
        self.form = InventorySearchForm(self.request.GET)
        if self.form.is_valid():
            queryset = self.form.filter_queryset(queryset)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = self.form
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
        return context


class InventoryDetailView( DetailView):
    """库存详情视图"""
    model = Inventory
    template_name = 'inventory/inventory_detail.html'
    context_object_name = 'inventory'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inventory = self.object
        
        # 获取相关交易记录
        context['transactions'] = WarehouseTransaction.objects.filter(
            product=inventory.product,
            warehouse=inventory.warehouse
        ).order_by('-transaction_date')[:10]
        
        # 获取相关预留记录
        from .models import StockReservation, ReservationAllocation
        context['reservations'] = StockReservation.objects.filter(
            product=inventory.product,
            status__in=['reserved', 'partially_reserved']
        ).order_by('-reserved_at')[:10]
        
        return context


class InventoryCreateView( CreateView):
    """创建库存记录视图"""
    model = Inventory
    form_class = InventoryForm
    template_name = 'inventory/inventory_form.html'
    success_url = reverse_lazy('inventory:inventory_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        with transaction.atomic():
            inventory = form.save()
            
            # 创建仓库交易记录
            WarehouseTransaction.objects.create(
                transaction_type='receiving',
                product=inventory.product,
                quantity=inventory.quantity,
                warehouse=inventory.warehouse,
                to_location=inventory.location,
                staff=self.request.user.staff_profile if hasattr(self.request.user, 'staff_profile') else None,
                reference_number=f'INV-{inventory.id}',
                notes=f'入库 {inventory.quantity} 件 {inventory.product.name}'
            )
            
            messages.success(self.request, f'已成功添加库存记录: {inventory.product.name} x {inventory.quantity}')
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '添加库存记录'
        return context


class InventoryUpdateView( UpdateView):
    """更新库存记录视图"""
    model = Inventory
    form_class = InventoryForm
    template_name = 'inventory/inventory_form.html'
    
    def get_success_url(self):
        return reverse_lazy('inventory:inventory_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        old_quantity = self.object.quantity
        old_location = self.object.location
        
        with transaction.atomic():
            inventory = form.save()
            
            # 检查数量变化
            quantity_change = inventory.quantity - old_quantity
            
            if quantity_change != 0:
                # 创建调整交易记录
                WarehouseTransaction.objects.create(
                    transaction_type='adjustment',
                    product=inventory.product,
                    quantity=quantity_change,
                    warehouse=inventory.warehouse,
                    from_location=old_location if old_location != inventory.location else None,
                    to_location=inventory.location if old_location != inventory.location else None,
                    staff=self.request.user.staff_profile if hasattr(self.request.user, 'staff_profile') else None,
                    reference_number=f'ADJ-{inventory.id}',
                    notes=f'库存调整: {quantity_change:+d} 件'
                )
            
            # 如果位置改变，需要调整容量
            if old_location != inventory.location:
                if old_location:
                    # 从旧位置移除
                    product_volume = inventory.product.volume if hasattr(inventory.product, 'volume') else 0
                    volume = old_quantity * product_volume
                    weight = 0
                    old_location.update_occupancy(volume, weight, 'decrease')
                
                if inventory.location:
                    # 添加到新位置
                    product_volume = inventory.product.volume if hasattr(inventory.product, 'volume') else 0
                    volume = inventory.quantity * product_volume
                    weight = 0
                    inventory.location.update_occupancy(volume, weight, 'increase')
            
            messages.success(self.request, f'已成功更新库存记录: {inventory.product.name}')
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '编辑库存记录'
        return context


class InventoryDeleteView(DeleteView):
    """删除库存记录视图"""
    model = Inventory
    template_name = 'inventory/inventory_confirm_delete.html'
    success_url = reverse_lazy('inventory:inventory_list')
    
    def delete(self, request, *args, **kwargs):
        inventory = self.get_object()
        
        with transaction.atomic():
            # 创建删除交易记录
            WarehouseTransaction.objects.create(
                transaction_type='adjustment',
                product=inventory.product,
                quantity=-inventory.quantity,
                warehouse=inventory.warehouse,
                from_location=inventory.location,
                staff=self.request.user.staff_profile if hasattr(self.request.user, 'staff_profile') else None,
                reference_number=f'DEL-{inventory.id}',
                notes=f'删除库存记录'
            )
            
            # 释放位置容量
            if inventory.location and inventory.product:
                product_volume = inventory.product.volume if hasattr(inventory.product, 'volume') else 0
                volume = inventory.quantity * product_volume
                weight = 0
                
                if volume > 0:
                    inventory.location.update_occupancy(volume, weight, 'decrease')
                    inventory.warehouse.update_capacity(volume, 'decrease')
            
            messages.success(request, f'已删除库存记录: {inventory.product.name} x {inventory.quantity}')
        
        return super().delete(request, *args, **kwargs)


class QuickAddInventoryView(CreateView):
    """快速添加入库视图（用于扫描）"""
    template_name = 'inventory/quick_add_inventory.html'
    form_class = QuickAddInventoryForm


    def get_form_kwargs(self):
        """为 Form（非 ModelForm）重写此方法，移除 instance"""
        kwargs = super().get_form_kwargs()
        # 移除 'instance'，因为 QuickAddInventoryForm 是 Form 而不是 ModelForm
        if 'instance' in kwargs:
            kwargs.pop('instance')
        return kwargs    
    

    def form_valid(self, form):
        from products.models import Product
        
        sku = form.cleaned_data['sku']
        warehouse = form.cleaned_data['warehouse']
        quantity = form.cleaned_data['quantity']
        batch_number = form.cleaned_data.get('batch_number')
        unit_cost = form.cleaned_data.get('unit_cost')
        
        try:
            product = Product.objects.get(sku=sku)
            
            with transaction.atomic():
                # 如果没有提供批次号，自动生成
                if not batch_number:
                    batch_number = f'{sku}-{timezone.now().strftime("%Y%m%d")}'
                
                # 如果没有提供单位成本，使用产品成本价
                if not unit_cost:
                    unit_cost = product.cost_price or 0
                
                # 查找或创建库存记录
                inventory, created = Inventory.objects.get_or_create(
                    product=product,
                    warehouse=warehouse,
                    batch_number=batch_number,
                    defaults={
                        'quantity': quantity,
                        'unit_cost': unit_cost,
                        'status': 'active'
                    }
                )
                
                if not created:
                    # 更新现有库存
                    inventory.quantity += quantity
                    inventory.save()
                
                # 创建交易记录
                WarehouseTransaction.objects.create(
                    transaction_type='receiving',
                    product=product,
                    quantity=quantity,
                    warehouse=warehouse,
                    staff=self.request.user.staff_profile if hasattr(self.request.user, 'staff_profile') else None,
                    reference_number=f'QR-{product.sku}',
                    notes=f'快速入库 {quantity} 件'
                )
                
                action = '添加' if created else '更新'
                messages.success(self.request, f'已{action}库存: {product.name} x {quantity}')
                
                # 如果是 AJAX 请求，返回 JSON 响应
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'已{action}库存',
                        'product_name': product.name,
                        'sku': product.sku,
                        'quantity': inventory.quantity,
                        'batch_number': batch_number
                    })
                
                return redirect('inventory:inventory_list')
        
        except Product.DoesNotExist:
            messages.error(self.request, f'找不到SKU为 {sku} 的产品')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        return super().form_invalid(form)


def get_product_by_sku(request):
    """通过SKU获取产品信息（AJAX）"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        sku = request.GET.get('sku')
        
        try:
            from products.models import Product
            product = Product.objects.get(sku=sku)
            
            return JsonResponse({
                'success': True,
                'product': {
                    'id': str(product.id),
                    'name': product.name,
                    'sku': product.sku,
                    'category': product.category.name if product.category else '',
                    'price': float(product.price),
                    'stock_quantity': product.stock_quantity,
                    'manage_stock': product.manage_stock,
                    'low_stock_threshold': product.low_stock_threshold,
                    'volume': float(product.volume) if hasattr(product, 'volume') else 0,
                }
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'找不到SKU为 {sku} 的产品'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


def get_locations_by_warehouse(request):
    """根据仓库获取存储位置（AJAX）"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        warehouse_id = request.GET.get('warehouse_id')
        
        try:
            locations = StorageLocation.objects.filter(
                warehouse_id=warehouse_id,
                is_active=True,
                is_full=False
            ).values('id', 'code', 'name', 'available_volume')
            
            return JsonResponse({
                'success': True,
                'locations': list(locations)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})
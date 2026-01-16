# inventory/services.py
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class InventoryService:
    """库存管理服务"""
    
    @staticmethod
    def check_product_availability(product_id, quantity=1, warehouse_id=None):
        """
        检查产品可用性
        
        Args:
            product_id: 产品ID
            quantity: 需要数量
            warehouse_id: 指定仓库ID（可选）
            
        Returns:
            tuple: (是否可用, 消息, 可用库存列表)
        """
        from .models import Inventory, Product
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return False, '产品不存在或已下架', []
        
        # 检查产品状态
        if not product.is_active_computed:
            return False, '产品已下架', []
        
        # 查询库存
        inventory_query = Inventory.objects.filter(
            product=product,
            status='active',
            available_quantity__gte=quantity
        )
        
        if warehouse_id:
            inventory_query = inventory_query.filter(warehouse_id=warehouse_id)
        
        available_inventories = list(inventory_query)
        
        if not available_inventories:
            # 检查是否允许缺货订购
            if not product.allow_backorders:
                return False, '库存不足', []
            return True, '允许缺货订购', []
        
        return True, '库存充足', available_inventories
    
    @staticmethod
    @transaction.atomic
    def reserve_stock(product_id, quantity, order_id=None, customer_id=None, warehouse_id=None):
        """
        预留库存
        
        Args:
            product_id: 产品ID
            quantity: 预留数量
            order_id: 关联订单ID（可选）
            customer_id: 客户ID（可选）
            warehouse_id: 指定仓库ID（可选）
            
        Returns:
            tuple: (是否成功, 消息, 预留记录)
        """
        from .models import Inventory, StockReservation
        
        # 检查可用性
        is_available, message, inventories = InventoryService.check_product_availability(
            product_id, quantity, warehouse_id
        )
        
        if not is_available:
            return False, message, None
        
        # 创建预留记录
        reservation = StockReservation(
            product_id=product_id,
            quantity=quantity,
            status='reserved',
            order_id=order_id,
            customer_id=customer_id
        )
        
        # 分配库存
        remaining_quantity = quantity
        allocated_inventories = []
        
        for inventory in inventories:
            if remaining_quantity <= 0:
                break
            
            # 分配数量（不超过库存可用量）
            allocate_qty = min(remaining_quantity, inventory.available_quantity)
            
            # 预留库存
            if inventory.reserve_stock(allocate_qty):
                # 记录分配详情
                allocated_inventories.append({
                    'inventory_id': inventory.id,
                    'quantity': allocate_qty
                })
                remaining_quantity -= allocate_qty
        
        # 如果还有剩余数量（允许缺货订购的情况）
        if remaining_quantity > 0:
            reservation.backorder_quantity = remaining_quantity
        
        reservation.save()
        
        # 保存分配详情
        for allocation in allocated_inventories:
            reservation.allocations.create(
                inventory_id=allocation['inventory_id'],
                quantity=allocation['quantity']
            )
        
        return True, '库存预留成功', reservation
    
    @staticmethod
    @transaction.atomic
    def release_stock(reservation_id):
        """
        释放预留库存
        
        Args:
            reservation_id: 预留记录ID
            
        Returns:
            tuple: (是否成功, 消息)
        """
        from .models import StockReservation
        
        try:
            reservation = StockReservation.objects.select_for_update().get(
                id=reservation_id,
                status__in=['reserved', 'partially_reserved']
            )
        except StockReservation.DoesNotExist:
            return False, '预留记录不存在或已释放'
        
        # 释放所有分配的库存
        for allocation in reservation.allocations.all():
            inventory = allocation.inventory
            inventory.release_stock(allocation.quantity)
        
        # 更新预留状态
        reservation.status = 'released'
        reservation.released_at = timezone.now()
        reservation.save()
        
        return True, '库存释放成功'
    
    @staticmethod
    @transaction.atomic
    def allocate_stock(reservation_id):
        """
        分配库存（预留转为实际出库）
        
        Args:
            reservation_id: 预留记录ID
            
        Returns:
            tuple: (是否成功, 消息)
        """
        from .models import StockReservation
        
        try:
            reservation = StockReservation.objects.select_for_update().get(
                id=reservation_id,
                status__in=['reserved', 'partially_reserved']
            )
        except StockReservation.DoesNotExist:
            return False, '预留记录不存在'
        
        # 验证所有分配是否足够
        total_allocated = reservation.allocations.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        if total_allocated < reservation.quantity - reservation.backorder_quantity:
            return False, '库存分配不足'
        
        # 执行库存分配
        for allocation in reservation.allocations.all():
            inventory = allocation.inventory
            if not inventory.allocate_stock(allocation.quantity):
                return False, f'库存分配失败: {inventory.product.name}'
        
        # 更新预留状态
        reservation.status = 'allocated'
        reservation.allocated_at = timezone.now()
        reservation.save()
        
        return True, '库存分配成功'
    
    @staticmethod
    def get_inventory_summary(warehouse_id=None, product_id=None):
        """
        获取库存摘要
        
        Returns:
            dict: 库存摘要信息
        """
        from .models import Inventory
        from django.db.models import Sum, Count, Avg
        
        query = Inventory.objects.filter(status='active')
        
        if warehouse_id:
            query = query.filter(warehouse_id=warehouse_id)
        
        if product_id:
            query = query.filter(product_id=product_id)
        
        summary = query.aggregate(
            total_quantity=Sum('quantity'),
            total_reserved=Sum('reserved_quantity'),
            total_available=Sum('available_quantity'),
            total_value=Sum('total_value'),
            product_count=Count('product', distinct=True),
            avg_unit_cost=Avg('unit_cost')
        )
        
        return {
            'total_quantity': summary['total_quantity'] or 0,
            'total_reserved': summary['total_reserved'] or 0,
            'total_available': summary['total_available'] or 0,
            'total_value': float(summary['total_value'] or 0),
            'product_count': summary['product_count'] or 0,
            'avg_unit_cost': float(summary['avg_unit_cost'] or 0),
        }
    
    @staticmethod
    def get_low_stock_products(threshold=None, warehouse_id=None):
        """
        获取低库存产品
        
        Args:
            threshold: 低库存阈值（可选）
            warehouse_id: 仓库ID（可选）
            
        Returns:
            QuerySet: 低库存产品列表
        """
        from .models import Inventory, Product
        
        query = Inventory.objects.filter(status='active')
        
        if warehouse_id:
            query = query.filter(warehouse_id=warehouse_id)
        
        if threshold is None:
            # 使用产品的低库存阈值
            query = query.annotate(
                low_threshold=models.F('product__low_stock_threshold')
            ).filter(
                models.Q(available_quantity__lte=models.F('low_threshold')) |
                models.Q(product__low_stock_threshold__gte=models.F('available_quantity'))
            )
        else:
            query = query.filter(available_quantity__lte=threshold)
        
        return query.select_related('product', 'warehouse').order_by('available_quantity')


class WarehouseService:
    """仓库管理服务"""
    
    @staticmethod
    def get_warehouse_capacity(warehouse_id):
        """
        获取仓库容量信息
        
        Returns:
            dict: 容量信息
        """
        from .models import Warehouse
        
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
            return warehouse.get_current_occupancy()
        except Warehouse.DoesNotExist:
            return None
    
    @staticmethod
    def find_best_location(product, quantity, warehouse):
        """
        查找最佳存储位置
        
        Args:
            product: 产品对象
            quantity: 数量
            warehouse: 仓库对象
            
        Returns:
            StorageLocation: 最佳存储位置，或None
        """
        from .models import StorageLocation
        
        # 计算产品体积
        product_volume = 0
        if product.length and product.width and product.height:
            product_volume = float(product.length * product.width * product.height) / 1000000  # 转换为立方米
        else:
            # 默认体积
            product_volume = 0.01  # 0.01立方米
        
        required_volume = product_volume * quantity
        
        # 查找合适的库位
        locations = StorageLocation.objects.filter(
            warehouse=warehouse,
            is_active=True,
            is_full=False,
            available_volume__gte=required_volume,
            available_weight__gte=product.weight or 0
        ).order_by('available_volume')
        
        # 优先选择已有相同产品的库位
        same_product_locations = locations.filter(
            inventory_items__product=product
        ).distinct()
        
        if same_product_locations.exists():
            return same_product_locations.first()
        
        return locations.first()
    
    @staticmethod
    @transaction.atomic
    def receive_stock(product_id, quantity, warehouse_id, batch_number=None, 
                      unit_cost=None, location_id=None):
        """
        接收库存（入库）
        
        Args:
            product_id: 产品ID
            quantity: 数量
            warehouse_id: 仓库ID
            batch_number: 批次号
            unit_cost: 单位成本
            location_id: 指定库位ID
            
        Returns:
            tuple: (是否成功, 消息, 库存记录)
        """
        from .models import Product, Warehouse, Inventory, StorageLocation
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            warehouse = Warehouse.objects.get(id=warehouse_id, is_active=True)
        except (Product.DoesNotExist, Warehouse.DoesNotExist) as e:
            return False, f'产品或仓库不存在: {str(e)}', None
        
        # 计算单位成本
        if unit_cost is None:
            unit_cost = product.cost_price
        
        # 查找或创建库存记录
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            batch_number=batch_number or '',
            defaults={
                'quantity': 0,
                'unit_cost': unit_cost
            }
        )
        
        # 如果没有指定库位，查找最佳库位
        if location_id:
            try:
                location = StorageLocation.objects.get(
                    id=location_id,
                    warehouse=warehouse,
                    is_active=True
                )
            except StorageLocation.DoesNotExist:
                return False, '指定的库位不存在', None
        else:
            location = WarehouseService.find_best_location(product, quantity, warehouse)
        
        # 更新库存
        inventory.quantity += quantity
        inventory.location = location
        inventory.save()
        
        # 更新库位占用
        if location:
            product_volume = 0
            if product.length and product.width and product.height:
                product_volume = float(product.length * product.width * product.height) / 1000000
            
            product_weight = float(product.weight or 0)
            
            location.update_occupancy(
                product_volume * quantity,
                product_weight * quantity,
                'increase'
            )
            
            # 更新仓库容量
            warehouse.update_capacity(product_volume * quantity, 'increase')
        
        return True, '库存接收成功', inventory
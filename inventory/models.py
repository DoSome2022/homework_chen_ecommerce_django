from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid
import logging

logger = logging.getLogger(__name__)


class WarehouseZone(models.Model):
    """倉庫區域"""
    ZONE_TYPES = [
        ('receiving', '收貨區'),
        ('storage', '存儲區'),
        ('picking', '揀貨區'),
        ('packing', '包裝區'),
        ('shipping', '發貨區'),
        ('quarantine', '隔離區'),
        ('returns', '退貨處理區'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.CASCADE, 
                                 related_name='zones')
    name = models.CharField('區域名稱', max_length=100)
    code = models.CharField('區域代碼', max_length=20, unique=True)
    zone_type = models.CharField('區域類型', max_length=20, choices=ZONE_TYPES)
    
    # 位置信息
    location_x = models.DecimalField('X坐標', max_digits=10, decimal_places=2, default=0)
    location_y = models.DecimalField('Y坐標', max_digits=10, decimal_places=2, default=0)
    location_z = models.DecimalField('Z坐標', max_digits=10, decimal_places=2, default=0)
    
    # 容量信息
    total_capacity = models.DecimalField('總容量(m³)', max_digits=10, decimal_places=2, 
                                        validators=[MinValueValidator(0)])
    used_capacity = models.DecimalField('已用容量(m³)', max_digits=10, decimal_places=2, default=0)
    
    # 溫度控制
    temperature_controlled = models.BooleanField('溫控區域', default=False)
    min_temperature = models.DecimalField('最低溫度(℃)', max_digits=5, decimal_places=2, 
                                         null=True, blank=True)
    max_temperature = models.DecimalField('最高溫度(℃)', max_digits=5, decimal_places=2, 
                                         null=True, blank=True)
    
    # 安全配置
    requires_access_code = models.BooleanField('需要訪問碼', default=False)
    access_level_required = models.IntegerField('所需訪問級別', default=1, 
                                               validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    is_active = models.BooleanField('是否啟用', default=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫區域'
        verbose_name_plural = '倉庫區域'
        ordering = ['warehouse', 'zone_type', 'code']
    
    def __str__(self):
        return f'{self.warehouse.name} - {self.name} ({self.get_zone_type_display()})'
    
    @property
    def available_capacity(self):
        return self.total_capacity - self.used_capacity
    
    @property
    def occupancy_rate(self):
        if self.total_capacity > 0:
            return (self.used_capacity / self.total_capacity) * 100
        return 0


class WarehouseAisle(models.Model):
    """倉庫通道"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.CASCADE, 
                                 related_name='aisles')
    zone = models.ForeignKey(WarehouseZone, on_delete=models.CASCADE, 
                            related_name='aisles', null=True, blank=True)
    aisle_number = models.CharField('通道編號', max_length=20)
    name = models.CharField('通道名稱', max_length=100, blank=True)
    
    # 尺寸信息
    length = models.DecimalField('長度(m)', max_digits=8, decimal_places=2, 
                                validators=[MinValueValidator(0)])
    width = models.DecimalField('寬度(m)', max_digits=8, decimal_places=2, 
                               validators=[MinValueValidator(0)])
    height = models.DecimalField('高度(m)', max_digits=8, decimal_places=2, 
                                validators=[MinValueValidator(0)])
    
    # 配置信息
    has_pallets = models.BooleanField('有托盤', default=True)
    pallet_configuration = models.JSONField('托盤配置', default=dict)
    max_weight_capacity = models.DecimalField('最大承重(kg)', max_digits=10, decimal_places=2, 
                                             validators=[MinValueValidator(0)])
    
    # 設備信息
    equipment = models.JSONField('設備配置', default=list)
    
    is_active = models.BooleanField('是否啟用', default=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫通道'
        verbose_name_plural = '倉庫通道'
        ordering = ['warehouse', 'aisle_number']
        unique_together = ['warehouse', 'aisle_number']
    
    def __str__(self):
        return f'{self.warehouse.name} - 通道 {self.aisle_number}'
    
    @property
    def volume(self):
        return self.length * self.width * self.height
    
    def get_shelves(self):
        """獲取通道內的所有貨架"""
        return self.shelves.all()


class WarehouseShelf(models.Model):
    """倉庫貨架"""
    SHELF_TYPES = [
        ('pallet_rack', '托盤貨架'),
        ('shelving_unit', '貨架單元'),
        ('cantilever', '懸臂架'),
        ('mezzanine', '閣樓貨架'),
        ('drive_in', '駛入式貨架'),
        ('push_back', '後推式貨架'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aisle = models.ForeignKey(WarehouseAisle, on_delete=models.CASCADE, related_name='shelves')
    shelf_number = models.CharField('貨架編號', max_length=20)
    name = models.CharField('貨架名稱', max_length=100, blank=True)
    shelf_type = models.CharField('貨架類型', max_length=20, choices=SHELF_TYPES, default='shelving_unit')
    
    # 位置信息
    position_x = models.DecimalField('X位置', max_digits=8, decimal_places=2, default=0)
    position_y = models.DecimalField('Y位置', max_digits=8, decimal_places=2, default=0)
    
    # 尺寸信息
    levels = models.IntegerField('層數', default=1, validators=[MinValueValidator(1)])
    bays = models.IntegerField('格數', default=1, validators=[MinValueValidator(1)])
    depth = models.DecimalField('深度(cm)', max_digits=8, decimal_places=2, 
                               validators=[MinValueValidator(0)])
    
    # 容量信息
    max_weight_per_level = models.DecimalField('每層最大承重(kg)', max_digits=10, decimal_places=2, 
                                              validators=[MinValueValidator(0)])
    max_items_per_bay = models.IntegerField('每格最大物品數', default=1)
    
    # 狀態信息
    current_weight = models.DecimalField('當前重量(kg)', max_digits=10, decimal_places=2, default=0)
    current_items = models.IntegerField('當前物品數', default=0)
    
    # 維護信息
    last_inspected = models.DateField('最後檢查日期', null=True, blank=True)
    inspection_due = models.DateField('下次檢查日期', null=True, blank=True)
    requires_maintenance = models.BooleanField('需要維護', default=False)
    maintenance_notes = models.TextField('維護備註', blank=True)
    
    is_active = models.BooleanField('是否啟用', default=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫貨架'
        verbose_name_plural = '倉庫貨架'
        ordering = ['aisle', 'shelf_number']
        unique_together = ['aisle', 'shelf_number']
    
    def __str__(self):
        return f'{self.aisle.warehouse.name} - 貨架 {self.shelf_number}'
    
    @property
    def total_capacity(self):
        return self.levels * self.bays * self.max_items_per_bay
    
    @property
    def available_capacity(self):
        return self.total_capacity - self.current_items
    
    @property
    def utilization_rate(self):
        if self.total_capacity > 0:
            return (self.current_items / self.total_capacity) * 100
        return 0
    
    def get_bin_locations(self):
        """獲取貨架上的所有庫位"""
        locations = []
        for level in range(1, self.levels + 1):
            for bay in range(1, self.bays + 1):
                location_code = f'{self.shelf_number}-{level:02d}-{bay:02d}'
                locations.append({
                    'code': location_code,
                    'level': level,
                    'bay': bay
                })
        return locations


class Warehouse(models.Model):
    """仓库"""
    WAREHOUSE_TYPES = [
        ('main', '主仓'),
        ('regional', '区域仓'),
        ('store', '门店仓'),
        ('fulfillment', '履约中心'),
        ('cold_storage', '冷链仓库'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField('仓库代码', max_length=20, unique=True)
    name = models.CharField('仓库名称', max_length=100)
    location = models.CharField('地理位置', max_length=200)
    
    # 联系信息
    contact_person = models.CharField('联系人', max_length=100)
    phone = models.CharField('联系电话', max_length=20)
    email = models.EmailField('邮箱')
    address = models.TextField('详细地址')
    
    # 仓库容量
    total_capacity = models.DecimalField('总容量(m³)', max_digits=10, decimal_places=2, 
                                        validators=[MinValueValidator(0)])
    used_capacity = models.DecimalField('已用容量(m³)', max_digits=10, decimal_places=2, 
                                       default=0, validators=[MinValueValidator(0)])
    
    # 运营信息
    is_active = models.BooleanField('是否启用', default=True)
    warehouse_type = models.CharField('仓库类型', max_length=50, choices=WAREHOUSE_TYPES)
    
    # 管理信息
    manager = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='managed_warehouses')
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '仓库'
        verbose_name_plural = '仓库'
        ordering = ['code']
    
    def __str__(self):
        return f'{self.name} ({self.code})'
    
    @property
    def available_capacity(self):
        return self.total_capacity - self.used_capacity
    
    @property
    def capacity_percentage(self):
        if self.total_capacity > 0:
            return (self.used_capacity / self.total_capacity) * 100
        return 0
    
    def get_current_occupancy(self):
        """获取当前占用率"""
        return {
            'total_capacity': float(self.total_capacity),
            'used_capacity': float(self.used_capacity),
            'available_capacity': float(self.available_capacity),
            'percentage': float(self.capacity_percentage)
        }
    
    def update_capacity(self, volume_change, action='increase'):
        """更新仓库容量"""
        if action == 'increase':
            self.used_capacity += volume_change
        elif action == 'decrease':
            self.used_capacity -= volume_change
        
        if self.used_capacity < 0:
            self.used_capacity = 0
        
        self.save()


class StorageLocation(models.Model):
    """存储位置（货架/库位）"""
    LOCATION_TYPES = [
        ('shelf', '货架'),
        ('bin', '货位'),
        ('pallet', '托盘'),
        ('floor', '地面'),
        ('rack', '货架位'),
        ('bulk', '散货区'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField('位置代码', max_length=50, unique=True)
    name = models.CharField('位置名称', max_length=100)
    location_type = models.CharField('位置类型', max_length=20, choices=LOCATION_TYPES)
    
    # 位置信息
    aisle = models.CharField('通道', max_length=20, blank=True)
    section = models.CharField('区域', max_length=20, blank=True)
    shelf = models.CharField('货架', max_length=20, blank=True)
    level = models.CharField('层数', max_length=20, blank=True)
    position = models.CharField('位置', max_length=20, blank=True)
    
    # 容量信息
    max_volume = models.DecimalField('最大容量(m³)', max_digits=10, decimal_places=2, 
                                    validators=[MinValueValidator(0)])
    max_weight = models.DecimalField('最大重量(kg)', max_digits=10, decimal_places=2, 
                                    validators=[MinValueValidator(0)])
    
    # 当前状态
    current_volume = models.DecimalField('当前容量(m³)', max_digits=10, decimal_places=2, default=0)
    current_weight = models.DecimalField('当前重量(kg)', max_digits=10, decimal_places=2, default=0)
    
    is_active = models.BooleanField('是否启用', default=True)
    is_full = models.BooleanField('是否已满', default=False)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '存储位置'
        verbose_name_plural = '存储位置'
        ordering = ['warehouse', 'code']
        unique_together = ['warehouse', 'code']
    
    def __str__(self):
        return f'{self.warehouse.code} - {self.code}'
    
    def update_occupancy(self, volume, weight, action='increase'):
        """更新占用情况"""
        if action == 'increase':
            self.current_volume += volume
            self.current_weight += weight
        elif action == 'decrease':
            self.current_volume -= volume
            self.current_weight -= weight
        
        # 检查是否已满
        if self.current_volume >= self.max_volume or self.current_weight >= self.max_weight:
            self.is_full = True
        else:
            self.is_full = False
        
        self.save()
    
    @property
    def available_volume(self):
        return self.max_volume - self.current_volume
    
    @property
    def available_weight(self):
        return self.max_weight - self.current_weight


class Inventory(models.Model):
    """库存记录"""
    STATUS_CHOICES = [
        ('active', '正常'),
        ('quarantine', '隔离'),
        ('damaged', '损坏'),
        ('expired', '过期'),
        ('reserved', '预留'),
        ('in_transit', '在途'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='inventory_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_items')
    location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='inventory_items')
    
    # 库存数量
    quantity = models.IntegerField('数量', default=0, validators=[MinValueValidator(0)])
    reserved_quantity = models.IntegerField('预留数量', default=0, validators=[MinValueValidator(0)])
    available_quantity = models.IntegerField('可用数量', default=0)
    
    # 批次信息
    batch_number = models.CharField('批次号', max_length=100, blank=True)
    manufacturing_date = models.DateField('生产日期', null=True, blank=True)
    expiry_date = models.DateField('过期日期', null=True, blank=True)
    
    # 成本信息
    unit_cost = models.DecimalField('单位成本', max_digits=10, decimal_places=2, 
                                   validators=[MinValueValidator(0)])
    total_value = models.DecimalField('总价值', max_digits=12, decimal_places=2, 
                                     validators=[MinValueValidator(0)])
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='active')
    
    last_updated = models.DateTimeField('最后更新', auto_now=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '库存记录'
        verbose_name_plural = '库存记录'
        ordering = ['warehouse', 'product']
        unique_together = ['product', 'warehouse', 'batch_number']
        indexes = [
            models.Index(fields=['product', 'warehouse']),
            models.Index(fields=['status', 'expiry_date']),
        ]
    
    def __str__(self):
        return f'{self.product.name} - {self.warehouse.name} - {self.quantity}'
    
    def save(self, *args, **kwargs):
        # 计算可用数量
        self.available_quantity = self.quantity - self.reserved_quantity
        
        # 计算总价值
        self.total_value = self.quantity * self.unit_cost
        
        super().save(*args, **kwargs)
        
        # 更新产品总库存
        self.update_product_stock()
    
    def update_product_stock(self):
        """更新产品总库存"""
        from django.db.models import Sum
        
        total_quantity = Inventory.objects.filter(
            product=self.product, 
            status='active'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        reserved_quantity = Inventory.objects.filter(
            product=self.product, 
            status='active'
        ).aggregate(total=Sum('reserved_quantity'))['total'] or 0
        
        self.product.stock_quantity = total_quantity
        self.product.is_in_stock = total_quantity > reserved_quantity
        self.product.save()
    
    def reserve_stock(self, quantity):
        """预留库存"""
        if self.available_quantity >= quantity:
            self.reserved_quantity += quantity
            self.save()
            return True
        return False
    
    def release_stock(self, quantity):
        """释放预留库存"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            self.save()
            return True
        return False
    
    def allocate_stock(self, quantity):
        """分配库存（预留转为实际出库）"""
        if self.reserved_quantity >= quantity and self.quantity >= quantity:
            self.quantity -= quantity
            self.reserved_quantity -= quantity
            self.save()
            
            # 更新仓库容量
            if self.location:
                product_volume = self.product.volume if hasattr(self.product, 'volume') else 0
                if product_volume:
                    volume_change = quantity * product_volume
                    self.location.update_occupancy(volume_change, 0, 'decrease')
                    self.warehouse.update_capacity(volume_change, 'decrease')
            
            return True
        return False
    
    def check_expiry(self):
        """检查是否过期"""
        if self.expiry_date:
            if timezone.now().date() > self.expiry_date:
                self.status = 'expired'
                self.save()
                return True
        return False


class StockReservation(models.Model):
    """库存预留记录"""
    RESERVATION_STATUS = [
        ('reserved', '已预留'),
        ('partially_reserved', '部分预留'),
        ('allocated', '已分配'),
        ('released', '已释放'),
        ('cancelled', '已取消'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_number = models.CharField('预留单号', max_length=50, unique=True)
    
    # 关联信息
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, 
                               related_name='reservations')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, 
                             null=True, blank=True, related_name='stock_reservations')
    customer = models.ForeignKey('accounts.Customer', on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='stock_reservations')
    
    # 数量信息
    quantity = models.IntegerField('预留数量', validators=[MinValueValidator(1)])
    backorder_quantity = models.IntegerField('缺货数量', default=0)
    
    # 状态信息
    status = models.CharField('状态', max_length=20, choices=RESERVATION_STATUS, default='reserved')
    expires_at = models.DateTimeField('过期时间', null=True, blank=True)
    
    # 时间信息
    reserved_at = models.DateTimeField('预留时间', auto_now_add=True)
    allocated_at = models.DateTimeField('分配时间', null=True, blank=True)
    released_at = models.DateTimeField('释放时间', null=True, blank=True)
    
    # 备注
    notes = models.TextField('备注', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '库存预留'
        verbose_name_plural = '库存预留'
        ordering = ['-reserved_at']
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f'{self.reservation_number} - {self.product.name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        if not self.reservation_number:
            self.reservation_number = self.generate_reservation_number()
        super().save(*args, **kwargs)
    
    def generate_reservation_number(self):
        """生成预留单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = StockReservation.objects.filter(
            reservation_number__startswith=f'RES{date_str}'
        ).count() + 1
        return f'RES{date_str}{count:04d}'
    
    @property
    def is_expired(self):
        """检查是否过期"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_allocate(self):
        """检查是否可以分配"""
        return self.status in ['reserved', 'partially_reserved'] and not self.is_expired


class ReservationAllocation(models.Model):
    """预留分配详情"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(StockReservation, on_delete=models.CASCADE, 
                                   related_name='allocations')
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, 
                                 related_name='allocations')
    
    quantity = models.IntegerField('分配数量', validators=[MinValueValidator(1)])
    
    allocated_at = models.DateTimeField('分配时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '预留分配'
        verbose_name_plural = '预留分配'
        unique_together = ['reservation', 'inventory']
    
    def __str__(self):
        return f'{self.reservation.reservation_number} - {self.inventory.product.name} x {self.quantity}'


class StockTransfer(models.Model):
    """库存调拨"""
    TRANSFER_STATUS = [
        ('pending', '待处理'),
        ('approved', '已批准'),
        ('in_transit', '运输中'),
        ('received', '已接收'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer_number = models.CharField('调拨单号', max_length=50, unique=True)
    
    # 调拨信息
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                      related_name='outgoing_transfers')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                    related_name='incoming_transfers')
    
    # 状态信息
    status = models.CharField('状态', max_length=20, choices=TRANSFER_STATUS, default='pending')
    priority = models.CharField('优先级', max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # 物流信息
    shipping_method = models.CharField('运输方式', max_length=100, blank=True)
    tracking_number = models.CharField('跟踪号码', max_length=100, blank=True)
    estimated_delivery = models.DateField('预计送达', null=True, blank=True)
    actual_delivery = models.DateField('实际送达', null=True, blank=True)
    
    # 人员信息
    requested_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                    null=True, related_name='requested_transfers')
    approved_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='approved_transfers')
    received_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='received_transfers')
    
    notes = models.TextField('备注', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '库存调拨'
        verbose_name_plural = '库存调拨'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.transfer_number} - {self.from_warehouse.name} → {self.to_warehouse.name}'
    
    def generate_transfer_number(self):
        """生成调拨单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = StockTransfer.objects.filter(
            transfer_number__startswith=f'TR{date_str}'
        ).count() + 1
        return f'TR{date_str}{count:04d}'
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            self.transfer_number = self.generate_transfer_number()
        super().save(*args, **kwargs)
    
    def get_total_items(self):
        """获取调拨项目总数"""
        from django.db.models import Sum
        return self.transfer_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    def get_total_value(self):
        """获取调拨总价值"""
        from django.db.models import Sum
        return self.transfer_items.aggregate(
            total=Sum(models.F('quantity') * models.F('unit_cost'))
        )['total'] or 0


class TransferItem(models.Model):
    """调拨项目"""
    ITEM_STATUS = [
        ('pending', '待处理'),
        ('picked', '已拣货'),
        ('shipped', '已发货'),
        ('received', '已接收'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='transfer_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.IntegerField('数量', validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField('单位成本', max_digits=10, decimal_places=2, 
                                   validators=[MinValueValidator(0)])
    total_cost = models.DecimalField('总成本', max_digits=12, decimal_places=2, 
                                    validators=[MinValueValidator(0)])
    
    # 批次信息
    batch_number = models.CharField('批次号', max_length=100, blank=True)
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=ITEM_STATUS, default='pending')
    
    notes = models.TextField('备注', blank=True)
    
    class Meta:
        verbose_name = '调拨项目'
        verbose_name_plural = '调拨项目'
        ordering = ['transfer', 'product']
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        # 计算总成本
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
    
    def allocate_from_inventory(self):
        """从库存分配"""
        if not self.inventory:
            # 查找源仓库的库存
            inventory = Inventory.objects.filter(
                product=self.product,
                warehouse=self.transfer.from_warehouse,
                status='active'
            ).first()
            
            if inventory and inventory.available_quantity >= self.quantity:
                self.inventory = inventory
                if inventory.reserve_stock(self.quantity):
                    self.status = 'picked'
                    self.save()
                    return True
        return False


class StockAdjustment(models.Model):
    """库存调整"""
    ADJUSTMENT_TYPES = [
        ('inventory_count', '库存盘点'),
        ('damaged', '损坏调整'),
        ('expired', '过期调整'),
        ('theft', '丢失调整'),
        ('transfer_error', '调拨误差'),
        ('other', '其他'),
    ]
    
    ADJUSTMENT_STATUS = [
        ('pending', '待审核'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
        ('completed', '已完成'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adjustment_number = models.CharField('调整单号', max_length=50, unique=True)
    
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField('调整类型', max_length=50, choices=ADJUSTMENT_TYPES)
    
    # 数量信息
    total_items = models.IntegerField('总项目数', default=0)
    total_value_change = models.DecimalField('总价值变化', max_digits=12, decimal_places=2, default=0)
    
    # 状态信息
    status = models.CharField('状态', max_length=20, choices=ADJUSTMENT_STATUS, default='pending')
    reason = models.TextField('调整原因')
    
    # 人员信息
    created_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                  null=True, related_name='created_adjustments')
    reviewed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='reviewed_adjustments')
    
    notes = models.TextField('备注', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '库存调整'
        verbose_name_plural = '库存调整'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.adjustment_number} - {self.get_adjustment_type_display()}'
    
    def generate_adjustment_number(self):
        """生成调整单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = StockAdjustment.objects.filter(
            adjustment_number__startswith=f'ADJ{date_str}'
        ).count() + 1
        return f'ADJ{date_str}{count:04d}'
    
    def save(self, *args, **kwargs):
        if not self.adjustment_number:
            self.adjustment_number = self.generate_adjustment_number()
        super().save(*args, **kwargs)
    
    def apply_adjustment(self):
        """应用库存调整"""
        if self.status != 'approved':
            return False
        
        for item in self.adjustment_items.all():
            inventory = item.inventory
            
            # 更新库存数量
            inventory.quantity += item.quantity_change
            if inventory.quantity < 0:
                inventory.quantity = 0
            
            # 更新库存状态
            if item.adjustment_reason in ['damaged', 'expired']:
                inventory.status = item.adjustment_reason
            
            inventory.save()
        
        self.status = 'completed'
        self.save()
        return True


class AdjustmentItem(models.Model):
    """调整项目"""
    ADJUSTMENT_REASONS = [
        ('damaged', '损坏'),
        ('expired', '过期'),
        ('counting_error', '盘点误差'),
        ('theft', '盗窃'),
        ('other', '其他'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adjustment = models.ForeignKey(StockAdjustment, on_delete=models.CASCADE, related_name='adjustment_items')
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    
    # 调整信息
    quantity_before = models.IntegerField('调整前数量')
    quantity_change = models.IntegerField('数量变化')
    quantity_after = models.IntegerField('调整后数量')
    
    unit_cost = models.DecimalField('单位成本', max_digits=10, decimal_places=2)
    value_change = models.DecimalField('价值变化', max_digits=12, decimal_places=2)
    
    # 调整原因
    adjustment_reason = models.CharField('调整原因', max_length=50, choices=ADJUSTMENT_REASONS)
    
    notes = models.TextField('备注', blank=True)
    
    class Meta:
        verbose_name = '调整项目'
        verbose_name_plural = '调整项目'
        ordering = ['adjustment', 'inventory']
    
    def __str__(self):
        return f'{self.inventory.product.name} - {self.quantity_change:+d}'
    
    def save(self, *args, **kwargs):
        # 计算调整后数量和价值变化
        self.quantity_after = self.quantity_before + self.quantity_change
        self.value_change = self.quantity_change * self.unit_cost
        super().save(*args, **kwargs)


class WarehouseTransaction(models.Model):
    """仓库交易记录"""
    TRANSACTION_TYPES = [
        ('receiving', '收货'),
        ('putaway', '上架'),
        ('picking', '拣货'),
        ('packing', '包装'),
        ('shipping', '发货'),
        ('adjustment', '调整'),
        ('transfer', '调拨'),
        ('return', '退货'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_number = models.CharField('交易编号', max_length=50, unique=True)
    
    # 交易信息
    transaction_type = models.CharField('交易类型', max_length=20, choices=TRANSACTION_TYPES)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, 
                               related_name='warehouse_transactions')
    quantity = models.IntegerField('数量', validators=[MinValueValidator(1)])
    
    # 仓库信息
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='transactions')
    from_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='transactions_from')
    to_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='transactions_to')
    
    # 关联信息
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, 
                             null=True, blank=True, related_name='warehouse_transactions')
    transfer = models.ForeignKey(StockTransfer, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='transactions')
    adjustment = models.ForeignKey(StockAdjustment, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='transactions')
    
    # 人员信息
    staff = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                             null=True, related_name='warehouse_transactions')
    
    # 时间信息
    transaction_date = models.DateTimeField('交易时间', auto_now_add=True)
    
    # 参考信息
    reference_number = models.CharField('参考编号', max_length=100, blank=True)
    notes = models.TextField('备注', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '仓库交易记录'
        verbose_name_plural = '仓库交易记录'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['transaction_type', 'transaction_date']),
            models.Index(fields=['product', 'warehouse']),
        ]
    
    def __str__(self):
        return f'{self.transaction_number} - {self.product.name} x {self.quantity}'
    
    def generate_transaction_number(self):
        """生成交易编号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = WarehouseTransaction.objects.filter(
            transaction_number__startswith=f'TXN{date_str}'
        ).count() + 1
        return f'TXN{date_str}{count:04d}'
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)
    
    def process_transaction(self):
        """处理交易"""
        try:
            # 根据交易类型执行相应操作
            if self.transaction_type == 'receiving':
                self._process_receiving()
            elif self.transaction_type == 'picking':
                self._process_picking()
            elif self.transaction_type == 'shipping':
                self._process_shipping()
            elif self.transaction_type == 'adjustment':
                self._process_adjustment()
            
            return True
        except Exception as e:
            logger.error(f'处理交易失败 {self.transaction_number}: {str(e)}')
            return False
    
    def _process_receiving(self):
        """处理收货交易"""
        # 实现收货逻辑
        pass
    
    def _process_picking(self):
        """处理拣货交易"""
        # 实现拣货逻辑
        pass


class WarehouseTask(models.Model):
    """倉庫任務"""
    TASK_TYPES = [
        ('receiving', '收貨'),
        ('putaway', '上架'),
        ('picking', '揀貨'),
        ('packing', '包裝'),
        ('shipping', '發貨'),
        ('inventory_check', '盤點'),
        ('stock_transfer', '調撥'),
        ('replenishment', '補貨'),
        ('maintenance', '維護'),
        ('cleaning', '清潔'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '緊急'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('assigned', '已分配'),
        ('in_progress', '進行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('on_hold', '暫停'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_number = models.CharField('任務編號', max_length=50, unique=True)
    
    # 任務信息
    task_type = models.CharField('任務類型', max_length=30, choices=TASK_TYPES)
    priority = models.CharField('優先級', max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField('任務狀態', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 關聯信息
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='tasks')
    related_order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='warehouse_tasks')
    related_shipment = models.ForeignKey('shipping.Shipment', on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='warehouse_tasks')
    related_transfer = models.ForeignKey(StockTransfer, on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='warehouse_tasks')
    
    # 任務詳情
    description = models.TextField('任務描述')
    instructions = models.TextField('操作說明', blank=True)
    
    # 時間信息
    estimated_duration = models.IntegerField('預計時長(分鐘)', null=True, blank=True)
    scheduled_start = models.DateTimeField('計劃開始時間', null=True, blank=True)
    scheduled_end = models.DateTimeField('計劃結束時間', null=True, blank=True)
    actual_start = models.DateTimeField('實際開始時間', null=True, blank=True)
    actual_end = models.DateTimeField('實際結束時間', null=True, blank=True)
    
    # 人員分配
    assigned_to = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                  null=True, related_name='created_tasks')
    completed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='completed_tasks')
    
    # 位置信息
    from_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='tasks_from')
    to_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='tasks_to')
    
    # 統計信息
    total_items = models.IntegerField('總物品數', default=0)
    items_completed = models.IntegerField('已完成物品數', default=0)
    total_weight = models.DecimalField('總重量(kg)', max_digits=10, decimal_places=2, default=0)
    
    # 備註
    notes = models.TextField('備註', blank=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫任務'
        verbose_name_plural = '倉庫任務'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['task_number']),
            models.Index(fields=['warehouse', 'status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f'{self.task_number} - {self.get_task_type_display()}'
    
    def generate_task_number(self):
        """生成任務編號"""
        import datetime
        task_type_prefix = {
            'receiving': 'RCV',
            'putaway': 'PUT',
            'picking': 'PCK',
            'packing': 'PAK',
            'shipping': 'SHP',
            'inventory_check': 'INV',
            'stock_transfer': 'TRF',
            'replenishment': 'REP',
            'maintenance': 'MNT',
            'cleaning': 'CLN',
        }
        prefix = task_type_prefix.get(self.task_type, 'TSK')
        date_str = datetime.datetime.now().strftime('%y%m%d')
        count = WarehouseTask.objects.filter(
            task_number__startswith=f'{prefix}{date_str}'
        ).count() + 1
        return f'{prefix}{date_str}{count:04d}'
    
    def save(self, *args, **kwargs):
        if not self.task_number:
            self.task_number = self.generate_task_number()
        super().save(*args, **kwargs)
    
    def assign_to_staff(self, staff):
        """分配任務給員工"""
        if staff.has_permission(f'warehouse_{self.task_type}'):
            self.assigned_to = staff
            self.status = 'assigned'
            self.save()
            
            # 發送任務通知
            self.send_assignment_notification()
            return True
        return False
    
    def start_task(self):
        """開始任務"""
        self.status = 'in_progress'
        self.actual_start = timezone.now()
        self.save()
    
    def complete_task(self, notes=''):
        """完成任務"""
        self.status = 'completed'
        self.actual_end = timezone.now()
        self.items_completed = self.total_items
        self.notes = notes
        self.completed_by = self.assigned_to
        self.save()
        
        # 更新相關對象狀態
        self.update_related_objects()
        
        # 發送完成通知
        self.send_completion_notification()
    
    def update_related_objects(self):
        """更新相關對象狀態"""
        if self.task_type == 'picking' and self.related_order:
            # 更新訂單揀貨狀態
            pass
        elif self.task_type == 'shipping' and self.related_shipment:
            # 更新發貨狀態
            pass  # 这里需要实现
    
    def send_assignment_notification(self):
        """發送任務分配通知"""
        from notifications.tasks import send_warehouse_task_assignment
        send_warehouse_task_assignment.delay(str(self.id))
    
    def send_completion_notification(self):
        """發送任務完成通知"""
        from notifications.tasks import send_warehouse_task_completion
        send_warehouse_task_completion.delay(str(self.id))


class TaskItem(models.Model):
    """任務項目"""
    ITEM_STATUS = [
        ('pending', '待處理'),
        ('in_progress', '進行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(WarehouseTask, on_delete=models.CASCADE, related_name='task_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    # variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, 
    #                            null=True, blank=True)
    
    # 數量信息
    quantity = models.IntegerField('數量', validators=[MinValueValidator(1)])
    quantity_completed = models.IntegerField('已完成數量', default=0)
    
    # 位置信息
    source_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='task_items_source')
    destination_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                           null=True, blank=True, related_name='task_items_dest')
    
    # 狀態信息
    status = models.CharField('狀態', max_length=20, choices=ITEM_STATUS, default='pending')
    
    # 掃描信息
    scanned_barcode = models.CharField('掃描條碼', max_length=100, blank=True)
    scan_time = models.DateTimeField('掃描時間', null=True, blank=True)
    scanned_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='scanned_items')
    
    # 錯誤信息
    has_error = models.BooleanField('有錯誤', default=False)
    error_type = models.CharField('錯誤類型', max_length=50, blank=True)
    error_description = models.TextField('錯誤描述', blank=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '任務項目'
        verbose_name_plural = '任務項目'
        ordering = ['task', 'product']
    
    def __str__(self):
        product_name = self.variant.name if self.variant else self.product.name
        return f'{self.task.task_number} - {product_name} x {self.quantity}'
    
    def scan_item(self, barcode, staff):
        """掃描物品"""
        # 驗證條碼
        is_valid = self.validate_barcode(barcode)
        
        if is_valid:
            self.scanned_barcode = barcode
            self.scan_time = timezone.now()
            self.scanned_by = staff
            self.quantity_completed += 1
            
            if self.quantity_completed >= self.quantity:
                self.status = 'completed'
            
            self.save()
            return True, '掃描成功'
        
        self.has_error = True
        self.error_type = 'invalid_barcode'
        self.error_description = f'無效條碼: {barcode}'
        self.save()
        return False, '條碼驗證失敗'
    
    def validate_barcode(self, barcode):
        """驗證條碼"""
        # 這裡實現條碼驗證邏輯
        # 可以是產品SKU、庫存批次號等
        return True


class PutawayTask(WarehouseTask):
    """上架任務 - 特殊化倉庫任務"""
    class Meta:
        # proxy = True
        verbose_name = '上架任務'
        verbose_name_plural = '上架任務'
    
    def create_from_receiving(self, receiving_document):
        """從收貨單創建上架任務"""
        # 實現收貨到上架的流程
        pass


class PickingTask(WarehouseTask):
    """揀貨任務 - 特殊化倉庫任務"""
    PICKING_METHODS = [
        ('single_order', '單訂單揀貨'),
        ('batch_picking', '批次揀貨'),
        ('zone_picking', '分區揀貨'),
        ('wave_picking', '波次揀貨'),
    ]
    
    picking_method = models.CharField('揀貨方法', max_length=20, choices=PICKING_METHODS, 
                                     default='single_order')
    pick_list = models.JSONField('揀貨清單', default=list)
    
    class Meta:
        # proxy = True
        verbose_name = '揀貨任務'
        verbose_name_plural = '揀貨任務'
    
    def generate_pick_list(self):
        """生成揀貨清單"""
        if self.related_order:
            items = []
            for order_item in self.related_order.order_items.all():
                # 查找庫存位置
                inventory = self.find_best_inventory(order_item.product, order_item.quantity)
                
                if inventory:
                    items.append({
                        'product_id': str(order_item.product.id),
                        'product_name': order_item.product.name,
                        'sku': order_item.product.sku,
                        'quantity': order_item.quantity,
                        'location': inventory.location.code if inventory.location else '',
                        'warehouse': inventory.warehouse.code,
                        'batch_number': inventory.batch_number
                    })
            
            self.pick_list = items
            self.total_items = len(items)
            self.save()
    
    def find_best_inventory(self, product, quantity):
        """查找最佳庫存位置"""
        # 實現庫存查找算法（FIFO, FEFO, LIFO等）
        inventories = product.inventory_records.filter(
            warehouse=self.warehouse,
            status='active',
            available_quantity__gte=quantity
        ).order_by('expiry_date', 'created_at')
        
        return inventories.first()


class WarehouseEquipment(models.Model):
    """倉庫設備"""
    EQUIPMENT_TYPES = [
        ('forklift', '叉車'),
        ('pallet_jack', '托盤車'),
        ('hand_truck', '手推車'),
        ('conveyor', '輸送帶'),
        ('scanner', '掃描槍'),
        ('printer', '打印機'),
        ('safety_equipment', '安全設備'),
        ('other', '其他'),
    ]
    
    STATUS_CHOICES = [
        ('available', '可用'),
        ('in_use', '使用中'),
        ('maintenance', '維修中'),
        ('out_of_service', '停用'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment_number = models.CharField('設備編號', max_length=50, unique=True)
    name = models.CharField('設備名稱', max_length=100)
    equipment_type = models.CharField('設備類型', max_length=30, choices=EQUIPMENT_TYPES)
    
    # 所屬信息
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='equipments')
    current_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='equipments')
    
    # 規格信息
    brand = models.CharField('品牌', max_length=100, blank=True)
    model = models.CharField('型號', max_length=100, blank=True)
    serial_number = models.CharField('序列號', max_length=100, blank=True)
    capacity = models.DecimalField('容量/負載(kg)', max_digits=10, decimal_places=2, 
                                  null=True, blank=True)
    specifications = models.JSONField('技術規格', default=dict)
    
    # 狀態信息
    status = models.CharField('設備狀態', max_length=20, choices=STATUS_CHOICES, default='available')
    last_maintenance = models.DateField('最後維護日期', null=True, blank=True)
    next_maintenance = models.DateField('下次維護日期', null=True, blank=True)
    maintenance_interval_days = models.IntegerField('維護間隔(天)', default=90)
    
    # 使用信息
    current_user = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='using_equipments')
    total_usage_hours = models.DecimalField('總使用小時', max_digits=10, decimal_places=2, default=0)
    
    # 安全信息
    requires_certification = models.BooleanField('需要證書', default=False)
    certification_expiry = models.DateField('證書有效期', null=True, blank=True)
    
    # 備註
    notes = models.TextField('備註', blank=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫設備'
        verbose_name_plural = '倉庫設備'
        ordering = ['warehouse', 'equipment_type', 'equipment_number']
    
    def __str__(self):
        return f'{self.equipment_number} - {self.name}'
    
    def check_maintenance_due(self):
        """檢查是否需要維護"""
        if self.next_maintenance:
            return timezone.now().date() >= self.next_maintenance
        return False
    
    def assign_to_staff(self, staff):
        """分配設備給員工"""
        if self.status == 'available':
            self.current_user = staff
            self.status = 'in_use'
            self.save()
            return True
        return False
    
    def return_equipment(self):
        """歸還設備"""
        self.current_user = None
        self.status = 'available'
        self.save()


class WarehouseStaffSchedule(models.Model):
    """倉庫員工排班"""
    SHIFT_TYPES = [
        ('morning', '早班'),
        ('afternoon', '中班'),
        ('night', '晚班'),
        ('overtime', '加班'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey('accounts.Staff', on_delete=models.CASCADE, 
                            related_name='warehouse_schedules')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='staff_schedules')
    
    # 排班信息
    shift_type = models.CharField('班次類型', max_length=20, choices=SHIFT_TYPES)
    work_date = models.DateField('工作日期')
    start_time = models.TimeField('開始時間')
    end_time = models.TimeField('結束時間')
    
    # 任務分配
    assigned_tasks = models.ManyToManyField(WarehouseTask, blank=True, 
                                           related_name='assigned_schedules')
    primary_zone = models.ForeignKey(WarehouseZone, on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='primary_staff')
    
    # 狀態信息
    is_working = models.BooleanField('是否在崗', default=False)
    clock_in_time = models.DateTimeField('打卡上班時間', null=True, blank=True)
    clock_out_time = models.DateTimeField('打卡下班時間', null=True, blank=True)
    actual_hours = models.DecimalField('實際工時', max_digits=5, decimal_places=2, default=0)
    
    # 績效信息
    tasks_completed = models.IntegerField('完成任務數', default=0)
    items_handled = models.IntegerField('處理物品數', default=0)
    productivity_score = models.DecimalField('生產力評分', max_digits=5, decimal_places=2, default=0)
    
    # 備註
    notes = models.TextField('備註', blank=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫員工排班'
        verbose_name_plural = '倉庫員工排班'
        ordering = ['work_date', 'start_time']
        unique_together = ['staff', 'work_date']
    
    def __str__(self):
        return f'{self.staff.user.username} - {self.work_date} - {self.get_shift_type_display()}'
    
    def clock_in(self):
        """打卡上班"""
        if not self.is_working:
            self.is_working = True
            self.clock_in_time = timezone.now()
            self.save()
            return True
        return False
    
    def clock_out(self):
        """打卡下班"""
        if self.is_working and self.clock_in_time:
            self.is_working = False
            self.clock_out_time = timezone.now()
            
            # 計算實際工時
            duration = self.clock_out_time - self.clock_in_time
            self.actual_hours = duration.total_seconds() / 3600
            
            self.save()
            return True
        return False
    
    def calculate_productivity(self):
        """計算生產力評分"""
        if self.actual_hours > 0:
            # 簡單的生產力計算：每小時處理的物品數
            self.productivity_score = self.items_handled / self.actual_hours
            self.save()


class WarehousePerformanceMetrics(models.Model):
    """倉庫績效指標"""
    PERIOD_TYPES = [
        ('daily', '日'),
        ('weekly', '周'),
        ('monthly', '月'),
        ('quarterly', '季'),
        ('yearly', '年'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='performance_metrics')
    
    # 時間維度
    metric_date = models.DateField('指標日期')
    period_type = models.CharField('期間類型', max_length=20, choices=PERIOD_TYPES)
    
    # 效率指標
    order_fulfillment_rate = models.DecimalField('訂單履行率(%)', max_digits=5, decimal_places=2, default=0)
    picking_accuracy = models.DecimalField('揀貨準確率(%)', max_digits=5, decimal_places=2, default=0)
    inventory_accuracy = models.DecimalField('庫存準確率(%)', max_digits=5, decimal_places=2, default=0)
    
    # 生產力指標
    orders_processed = models.IntegerField('處理訂單數', default=0)
    items_picked = models.IntegerField('揀貨物品數', default=0)
    items_packed = models.IntegerField('包裝物品數', default=0)
    shipments_processed = models.IntegerField('處理發貨單數', default=0)
    
    # 時間指標
    average_picking_time = models.DecimalField('平均揀貨時間(分鐘)', max_digits=8, decimal_places=2, default=0)
    average_packing_time = models.DecimalField('平均包裝時間(分鐘)', max_digits=8, decimal_places=2, default=0)
    order_cycle_time = models.DecimalField('訂單周期時間(小時)', max_digits=8, decimal_places=2, default=0)
    
    # 成本指標
    labor_cost = models.DecimalField('人力成本', max_digits=12, decimal_places=2, default=0)
    equipment_cost = models.DecimalField('設備成本', max_digits=12, decimal_places=2, default=0)
    cost_per_order = models.DecimalField('每訂單成本', max_digits=10, decimal_places=2, default=0)
    cost_per_item = models.DecimalField('每物品成本', max_digits=10, decimal_places=2, default=0)
    
    # 質量指標
    shipping_errors = models.IntegerField('發貨錯誤數', default=0)
    returns_due_to_errors = models.IntegerField('因錯誤退貨數', default=0)
    damaged_items = models.IntegerField('損壞物品數', default=0)
    
    # 利用率指標
    space_utilization = models.DecimalField('空間利用率(%)', max_digits=5, decimal_places=2, default=0)
    equipment_utilization = models.DecimalField('設備利用率(%)', max_digits=5, decimal_places=2, default=0)
    labor_utilization = models.DecimalField('人力利用率(%)', max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫績效指標'
        verbose_name_plural = '倉庫績效指標'
        ordering = ['-metric_date']
        unique_together = ['warehouse', 'metric_date', 'period_type']
    
    def __str__(self):
        return f'{self.warehouse.name} - {self.metric_date} - {self.get_period_type_display()}'
    
    @classmethod
    def calculate_daily_metrics(cls, warehouse, date):
        """計算每日績效指標"""
        from django.db.models import Count, Avg, Sum
        from datetime import timedelta
        
        metrics, created = cls.objects.get_or_create(
            warehouse=warehouse,
            metric_date=date,
            period_type='daily',
            defaults={}
        )
        
        # 計算效率指標
        total_orders = warehouse.orders.filter(
            created_at__date=date,
            status='completed'
        ).count()
        
        on_time_orders = warehouse.orders.filter(
            created_at__date=date,
            status='completed',
            completed_at__lte=models.F('created_at') + timedelta(hours=24)
        ).count()
        
        if total_orders > 0:
            metrics.order_fulfillment_rate = (on_time_orders / total_orders) * 100
        
        # 計算生產力指標
        metrics.orders_processed = total_orders
        
        # 計算錯誤率
        error_orders = warehouse.orders.filter(
            created_at__date=date,
            returns__status='approved',
            returns__reason__code__in=['wrong_item', 'damaged', 'defective']
        ).count()
        
        if total_orders > 0:
            metrics.shipping_errors = error_orders
        
        metrics.save()
        return metrics


class WarehouseSafetyCheck(models.Model):
    """倉庫安全檢查"""
    CHECK_TYPES = [
        ('daily', '每日檢查'),
        ('weekly', '每周檢查'),
        ('monthly', '每月檢查'),
        ('equipment', '設備檢查'),
        ('fire_safety', '消防安全'),
        ('emergency', '應急檢查'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待檢查'),
        ('in_progress', '檢查中'),
        ('completed', '已完成'),
        ('failed', '不合格'),
        ('corrected', '已糾正'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='safety_checks')
    check_type = models.CharField('檢查類型', max_length=20, choices=CHECK_TYPES)
    
    # 檢查信息
    checklist = models.JSONField('檢查清單', default=list)
    status = models.CharField('檢查狀態', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 檢查結果
    passed_items = models.IntegerField('通過項目數', default=0)
    failed_items = models.IntegerField('未通過項目數', default=0)
    total_items = models.IntegerField('總項目數', default=0)
    
    # 問題記錄
    issues_found = models.JSONField('發現問題', default=list)
    corrective_actions = models.JSONField('糾正措施', default=list)
    
    # 人員信息
    conducted_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                    null=True, related_name='conducted_safety_checks')
    reviewed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='reviewed_safety_checks')
    
    # 時間信息
    scheduled_date = models.DateField('計劃檢查日期')
    conducted_date = models.DateField('實際檢查日期', null=True, blank=True)
    next_check_date = models.DateField('下次檢查日期', null=True, blank=True)
    
    # 備註
    notes = models.TextField('備註', blank=True)
    
    created_at = models.DateTimeField('創建時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    
    class Meta:
        verbose_name = '倉庫安全檢查'
        verbose_name_plural = '倉庫安全檢查'
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f'{self.warehouse.name} - {self.get_check_type_display()} - {self.scheduled_date}'
    
    def conduct_check(self, staff, results):
        """進行安全檢查"""
        self.conducted_by = staff
        self.conducted_date = timezone.now().date()
        self.status = 'in_progress'
        
        # 處理檢查結果
        self.process_results(results)
        
        self.save()
    
    def process_results(self, results):
        """處理檢查結果"""
        passed = 0
        failed = 0
        issues = []
        
        for item in results:
            if item['passed']:
                passed += 1
            else:
                failed += 1
                issues.append({
                    'item': item['name'],
                    'description': item['description'],
                    'severity': item.get('severity', 'low'),
                    'required_action': item.get('required_action', '')
                })
        
        self.passed_items = passed
        self.failed_items = failed
        self.total_items = len(results)
        self.issues_found = issues
        
        if failed == 0:
            self.status = 'completed'
        else:
            self.status = 'failed'
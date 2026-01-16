from django.db import models
from django.core.validators import MinValueValidator
import uuid

class ShippingMethod(models.Model):
    """配送方式"""
    METHOD_TYPES = [
        ('standard', '标准配送'),
        ('express', '快递'),
        ('overnight', '隔夜达'),
        ('same_day', '当日达'),
        ('pickup', '自提'),
        ('international', '国际配送'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('配送方式名称', max_length=100)
    code = models.CharField('配送方式代码', max_length=50, unique=True)
    method_type = models.CharField('配送类型', max_length=50, choices=METHOD_TYPES, default='standard')
    
    # 价格配置
    is_free = models.BooleanField('是否免费', default=False)
    base_cost = models.DecimalField('基础费用', max_digits=10, decimal_places=2, 
                                   default=0, validators=[MinValueValidator(0)])
    cost_per_kg = models.DecimalField('每公斤费用', max_digits=10, decimal_places=2, 
                                     default=0, validators=[MinValueValidator(0)])
    cost_per_item = models.DecimalField('每件费用', max_digits=10, decimal_places=2, 
                                       default=0, validators=[MinValueValidator(0)])
    free_shipping_threshold = models.DecimalField('免运费阈值', max_digits=10, decimal_places=2, 
                                                 null=True, blank=True)
    
    # 时间配置
    estimated_days_min = models.IntegerField('最短预计天数', default=3)
    estimated_days_max = models.IntegerField('最长预计天数', default=7)
    cutoff_time = models.TimeField('当日截止时间', null=True, blank=True)
    
    # 区域限制
    available_countries = models.JSONField('可用国家', default=list)
    available_regions = models.JSONField('可用地区', default=list)
    available_postal_codes = models.JSONField('可用邮编范围', default=list)
    
    # 重量和尺寸限制
    max_weight = models.DecimalField('最大重量(kg)', max_digits=10, decimal_places=2, 
                                    null=True, blank=True)
    max_length = models.DecimalField('最大长度(cm)', max_digits=10, decimal_places=2, 
                                    null=True, blank=True)
    max_width = models.DecimalField('最大宽度(cm)', max_digits=10, decimal_places=2, 
                                   null=True, blank=True)
    max_height = models.DecimalField('最大高度(cm)', max_digits=10, decimal_places=2, 
                                    null=True, blank=True)
    max_volume = models.DecimalField('最大体积(m³)', max_digits=10, decimal_places=2, 
                                    null=True, blank=True)
    
    # 状态配置
    is_active = models.BooleanField('是否激活', default=True)
    display_order = models.IntegerField('显示顺序', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '配送方式'
        verbose_name_plural = '配送方式'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    def calculate_shipping_cost(self, order_amount=0, weight=0, item_count=0):
        """计算运费"""
        if self.is_free:
            return 0
        
        if self.free_shipping_threshold and order_amount >= self.free_shipping_threshold:
            return 0
        
        cost = self.base_cost
        cost += weight * self.cost_per_kg
        cost += item_count * self.cost_per_item
        
        return max(cost, 0)
    
    def is_available_for_address(self, address):
        """检查是否适用于指定地址"""
        country = address.get('country', '')
        region = address.get('region', '')
        postal_code = address.get('postal_code', '')
        
        if self.available_countries and country not in self.available_countries:
            return False
        
        if self.available_regions and region not in self.available_regions:
            return False
        
        if self.available_postal_codes:
            # 简化检查：实际应用中需要更复杂的邮编范围检查
            for code_range in self.available_postal_codes:
                if postal_code.startswith(code_range):
                    break
            else:
                return False
        
        return True

class Shipment(models.Model):
    """发货单"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('packing', '包装中'),
        ('ready', '准备发货'),
        ('shipped', '已发货'),
        ('in_transit', '运输中'),
        ('out_for_delivery', '配送中'),
        ('delivered', '已送达'),
        ('failed', '投递失败'),
        ('returned', '已退回'),
        ('cancelled', '已取消'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment_number = models.CharField('发货单号', max_length=50, unique=True)
    
    # 关联订单
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='shipments')
    
    # 配送信息
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT, 
                                       related_name='shipments')
    shipping_cost = models.DecimalField('运费', max_digits=10, decimal_places=2, default=0)
    
    # 状态信息
    status = models.CharField('发货状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    tracking_number = models.CharField('追踪号码', max_length=100, blank=True)
    tracking_url = models.URLField('追踪网址', blank=True)
    
    # 地址信息
    shipping_address = models.JSONField('配送地址', default=dict)
    
    # 包裹信息
    package_count = models.IntegerField('包裹数量', default=1)
    total_weight = models.DecimalField('总重量(kg)', max_digits=10, decimal_places=2, default=0)
    total_volume = models.DecimalField('总体积(m³)', max_digits=10, decimal_places=2, default=0)
    
    # 承运商信息
    carrier_name = models.CharField('承运商', max_length=100, blank=True)
    carrier_service = models.CharField('承运服务', max_length=100, blank=True)
    
    # 时间信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    shipped_at = models.DateTimeField('发货时间', null=True, blank=True)
    estimated_delivery = models.DateTimeField('预计送达时间', null=True, blank=True)
    delivered_at = models.DateTimeField('实际送达时间', null=True, blank=True)
    
    # 人员信息
    packed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                 null=True, blank=True, related_name='packed_shipments')
    shipped_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='shipped_shipments')
    
    # 备注
    notes = models.TextField('备注', blank=True)
    
    class Meta:
        verbose_name = '发货单'
        verbose_name_plural = '发货单'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shipment_number']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['tracking_number']),
        ]
    
    def __str__(self):
        return f'{self.shipment_number} - {self.order.order_number}'
    
    def generate_shipment_number(self):
        """生成发货单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = Shipment.objects.filter(
            shipment_number__startswith=f'SHP{date_str}'
        ).count() + 1
        return f'SHP{date_str}{count:06d}'
    
    def save(self, *args, **kwargs):
        if not self.shipment_number:
            self.shipment_number = self.generate_shipment_number()
        super().save(*args, **kwargs)
    
    @classmethod
    def create_from_order(cls, order):
        """从订单创建发货单"""
        # 计算订单总重量和体积
        total_weight = 0
        total_volume = 0
        
        for item in order.order_items.all():
            if item.product.weight:
                total_weight += item.quantity * item.product.weight
            if item.product.length and item.product.width and item.product.height:
                item_volume = item.product.length * item.product.width * item.product.height / 1000000  # 转为立方米
                total_volume += item.quantity * item_volume
        
        # 创建发货单
        shipment = cls.objects.create(
            order=order,
            shipping_method=ShippingMethod.objects.get(code='standard'),  # 默认标准配送
            shipping_cost=order.shipping_amount,
            shipping_address=order.shipping_address,
            total_weight=total_weight,
            total_volume=total_volume,
            carrier_name='默认承运商',
            estimated_delivery=timezone.now() + timedelta(days=3)
        )
        
        # 创建发货项目
        for item in order.order_items.all():
            ShipmentItem.objects.create(
                shipment=shipment,
                order_item=item,
                quantity=item.quantity
            )
        
        return shipment
    
    def mark_as_shipped(self, tracking_number, carrier_name=None):
        """标记为已发货"""
        self.status = 'shipped'
        self.tracking_number = tracking_number
        if carrier_name:
            self.carrier_name = carrier_name
        self.shipped_at = timezone.now()
        self.save()
        
        # 更新订单发货状态
        self.update_order_fulfillment_status()
        
        # 发送发货通知
        self.send_shipping_notification()
    
    def mark_as_delivered(self):
        """标记为已送达"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
        
        # 更新订单状态
        self.order.fulfillment_status = 'delivered'
        if self.order.status == 'processing':
            self.order.status = 'completed'
            self.order.completed_at = timezone.now()
        self.order.save()
    
    def update_order_fulfillment_status(self):
        """更新订单发货状态"""
        shipped_items = 0
        total_items = 0
        
        for item in self.shipment_items.all():
            shipped_items += item.quantity
            total_items += item.order_item.quantity
        
        if shipped_items == 0:
            self.order.fulfillment_status = 'unfulfilled'
        elif shipped_items < total_items:
            self.order.fulfillment_status = 'partially_fulfilled'
        else:
            self.order.fulfillment_status = 'fulfilled'
        
        self.order.save()
    
    def send_shipping_notification(self):
        """发送发货通知"""
        from notifications.tasks import send_shipping_notification_email
        send_shipping_notification_email.delay(str(self.id))

class ShipmentItem(models.Model):
    """发货项目"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='shipment_items')
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.CASCADE, 
                                  related_name='shipment_items')
    
    quantity = models.IntegerField('数量', validators=[MinValueValidator(1)])
    
    # 包裹信息
    package_number = models.CharField('包裹编号', max_length=50, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '发货项目'
        verbose_name_plural = '发货项目'
        unique_together = ['shipment', 'order_item']
    
    def __str__(self):
        return f'{self.shipment.shipment_number} - {self.order_item.product.name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # 更新订单项目的已发货数量
        self.order_item.quantity_shipped += self.quantity
        self.order_item.save()

class Carrier(models.Model):
    """承运商"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('承运商名称', max_length=100)
    code = models.CharField('承运商代码', max_length=50, unique=True)
    
    # 联系信息
    contact_person = models.CharField('联系人', max_length=100, blank=True)
    phone = models.CharField('电话', max_length=20, blank=True)
    email = models.EmailField('邮箱', blank=True)
    website = models.URLField('网站', blank=True)
    
    # API 配置
    api_integrated = models.BooleanField('API集成', default=False)
    api_config = models.JSONField('API配置', default=dict)
    
    # 服务配置
    services = models.JSONField('服务列表', default=list)
    tracking_url_template = models.CharField('追踪网址模板', max_length=500, blank=True)
    
    # 状态
    is_active = models.BooleanField('是否激活', default=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '承运商'
        verbose_name_plural = '承运商'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def generate_tracking_url(self, tracking_number):
        """生成追踪网址"""
        if self.tracking_url_template:
            return self.tracking_url_template.format(tracking_number=tracking_number)
        return ''
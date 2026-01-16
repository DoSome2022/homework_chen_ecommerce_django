from django.db import models
from django.core.validators import MinValueValidator
import uuid

class ReturnReason(models.Model):
    """退货原因"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('原因名称', max_length=100)
    code = models.CharField('原因代码', max_length=50, unique=True)
    description = models.TextField('描述', blank=True)
    requires_explanation = models.BooleanField('需要说明', default=False)
    requires_photos = models.BooleanField('需要照片', default=False)
    is_active = models.BooleanField('是否激活', default=True)
    display_order = models.IntegerField('显示顺序', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '退货原因'
        verbose_name_plural = '退货原因'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name

class ReturnRequest(models.Model):
    """退货申请"""
    STATUS_CHOICES = [
        ('requested', '已申请'),
        ('reviewing', '审核中'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
        ('waiting_for_return', '等待退货'),
        ('received', '已收到退货'),
        ('inspecting', '检查中'),
        ('refunded', '已退款'),
        ('exchanged', '已换货'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    TYPE_CHOICES = [
        ('refund', '退款'),
        ('exchange', '换货'),
        ('store_credit', '商店信用'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_number = models.CharField('退货单号', max_length=50, unique=True)
    
    # 关联信息
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='return_requests')
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, 
                                related_name='return_requests')
    
    # 退货信息
    return_type = models.CharField('退货类型', max_length=20, choices=TYPE_CHOICES)
    status = models.CharField('退货状态', max_length=30, choices=STATUS_CHOICES, default='requested')
    
    # 原因和说明
    reason = models.ForeignKey(ReturnReason, on_delete=models.PROTECT, related_name='returns')
    explanation = models.TextField('详细说明', blank=True)
    
    # 金额信息
    requested_refund_amount = models.DecimalField('申请退款金额', max_digits=12, decimal_places=2, 
                                                 default=0, validators=[MinValueValidator(0)])
    approved_refund_amount = models.DecimalField('批准退款金额', max_digits=12, decimal_places=2, 
                                                default=0, validators=[MinValueValidator(0)])
    actual_refund_amount = models.DecimalField('实际退款金额', max_digits=12, decimal_places=2, 
                                              default=0, validators=[MinValueValidator(0)])
    
    # 物流信息
    return_shipping_method = models.CharField('退货物流方式', max_length=100, blank=True)
    return_tracking_number = models.CharField('退货追踪号码', max_length=100, blank=True)
    return_carrier = models.CharField('退货承运商', max_length=100, blank=True)
    
    # 照片证据
    photos = models.JSONField('照片证据', default=list)
    
    # 处理信息
    notes = models.TextField('处理备注', blank=True)
    internal_notes = models.TextField('内部备注', blank=True)
    
    # 人员信息
    reviewed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='reviewed_returns')
    processed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='processed_returns')
    
    # 时间信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    requested_at = models.DateTimeField('申请时间', auto_now_add=True)
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)
    received_at = models.DateTimeField('收到退货时间', null=True, blank=True)
    refunded_at = models.DateTimeField('退款时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    class Meta:
        verbose_name = '退货申请'
        verbose_name_plural = '退货申请'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['return_number']),
            models.Index(fields=['order', 'status']),
        ]
    
    def __str__(self):
        return f'{self.return_number} - {self.order.order_number}'
    
    def generate_return_number(self):
        """生成退货单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = ReturnRequest.objects.filter(
            return_number__startswith=f'RET{date_str}'
        ).count() + 1
        return f'RET{date_str}{count:06d}'
    
    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self.generate_return_number()
        super().save(*args, **kwargs)
    
    def calculate_requested_amount(self):
        """计算申请退款金额"""
        total = 0
        for item in self.return_items.all():
            total += item.requested_refund_amount
        self.requested_refund_amount = total
        self.save()
    
    def approve(self, refund_amount=None, notes=''):
        """批准退货申请"""
        if refund_amount is None:
            refund_amount = self.requested_refund_amount
        
        self.status = 'approved'
        self.approved_refund_amount = refund_amount
        self.reviewed_by = self.reviewed_by  # 需要在视图中设置
        self.approved_at = timezone.now()
        self.notes = notes
        self.save()
        
        # 发送批准通知
        self.send_approval_notification()
    
    def reject(self, reason, notes=''):
        """拒绝退货申请"""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.notes = f'拒绝原因: {reason}\n{notes}'
        self.save()
        
        # 发送拒绝通知
        self.send_rejection_notification()
    
    def mark_as_received(self):
        """标记为已收到退货"""
        self.status = 'received'
        self.received_at = timezone.now()
        self.save()
        
        # 检查退货商品
        self.inspect_returned_items()
    
    def inspect_returned_items(self):
        """检查退货商品"""
        all_good = True
        inspection_notes = []
        
        for item in self.return_items.all():
            if item.condition == 'damaged':
                all_good = False
                inspection_notes.append(f'{item.product_name}: 商品损坏')
            elif item.condition == 'used':
                inspection_notes.append(f'{item.product_name}: 商品已使用')
            elif item.condition == 'wrong_item':
                all_good = False
                inspection_notes.append(f'{item.product_name}: 退回商品错误')
        
        if all_good:
            self.status = 'refunded'
            self.process_refund()
        else:
            self.status = 'inspecting'
            self.internal_notes = '\n'.join(inspection_notes)
        
        self.save()
    
    def process_refund(self):
        """处理退款"""
        from payments.models import Refund
        
        # 查找对应的支付记录
        payment = self.order.payments.filter(status='completed').first()
        
        if payment:
            # 创建退款
            success, message = payment.refund(self.approved_refund_amount)
            
            if success:
                self.status = 'refunded'
                self.actual_refund_amount = self.approved_refund_amount
                self.refunded_at = timezone.now()
                self.save()
                
                # 更新退货商品状态
                for item in self.return_items.all():
                    item.actual_refund_amount = item.calculate_actual_refund()
                    item.status = 'refunded'
                    item.save()
                
                # 重新入库
                self.restock_items()
            else:
                self.internal_notes = f'退款失败: {message}'
                self.save()
    
    def restock_items(self):
        """重新入库"""
        for item in self.return_items.all():
            # 查找库存记录
            inventory = Inventory.objects.filter(
                product=item.order_item.product,
                warehouse__is_active=True,
                status='active'
            ).first()
            
            if inventory:
                inventory.quantity += item.quantity
                inventory.save()
                
                item.restocked = True
                item.save()
    
    def send_approval_notification(self):
        """发送批准通知"""
        from notifications.tasks import send_return_approval_notification
        send_return_approval_notification.delay(str(self.id))
    
    def send_rejection_notification(self):
        """发送拒绝通知"""
        from notifications.tasks import send_return_rejection_notification
        send_return_rejection_notification.delay(str(self.id))

class ReturnItem(models.Model):
    """退货商品"""
    CONDITION_CHOICES = [
        ('new', '全新未使用'),
        ('like_new', '几乎全新'),
        ('used', '已使用'),
        ('damaged', '损坏'),
        ('defective', '有缺陷'),
        ('wrong_item', '错误商品'),
        ('missing_parts', '缺少零件'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('received', '已收到'),
        ('inspected', '已检查'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
        ('refunded', '已退款'),
        ('exchanged', '已换货'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, 
                                      related_name='return_items')
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.CASCADE, 
                                  related_name='return_items')
    
    # 退货信息
    quantity = models.IntegerField('退货数量', validators=[MinValueValidator(1)])
    condition = models.CharField('商品状况', max_length=20, choices=CONDITION_CHOICES, default='used')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 退款信息
    requested_refund_amount = models.DecimalField('申请退款金额', max_digits=10, decimal_places=2, 
                                                 default=0, validators=[MinValueValidator(0)])
    actual_refund_amount = models.DecimalField('实际退款金额', max_digits=10, decimal_places=2, 
                                              default=0, validators=[MinValueValidator(0)])
    
    # 换货信息
    exchange_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='exchanged_for')
    # exchange_variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, 
    #                                     null=True, blank=True, related_name='exchanged_for')
    
    # 检查信息
    inspection_notes = models.TextField('检查备注', blank=True)
    restocked = models.BooleanField('已重新入库', default=False)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '退货商品'
        verbose_name_plural = '退货商品'
        ordering = ['return_request', 'order_item']
        unique_together = ['return_request', 'order_item']
    
    def __str__(self):
        return f'{self.return_request.return_number} - {self.product_name} x {self.quantity}'
    
    @property
    def product_name(self):
        return self.order_item.product_name
    
    def save(self, *args, **kwargs):
        # 计算申请退款金额
        if self.requested_refund_amount == 0:
            self.requested_refund_amount = self.calculate_requested_refund()
        
        super().save(*args, **kwargs)
        
        # 更新退货申请的总金额
        self.return_request.calculate_requested_amount()
    
    def calculate_requested_refund(self):
        """计算申请退款金额"""
        unit_price = self.order_item.unit_price
        
        # 根据商品状况调整退款金额
        if self.condition == 'new':
            refund_rate = 1.0
        elif self.condition == 'like_new':
            refund_rate = 0.9
        elif self.condition == 'used':
            refund_rate = 0.7
        elif self.condition == 'damaged':
            refund_rate = 0.3
        elif self.condition == 'defective':
            refund_rate = 1.0  # 有缺陷全额退款
        else:
            refund_rate = 0.5
        
        return unit_price * self.quantity * refund_rate
    
    def calculate_actual_refund(self):
        """计算实际退款金额"""
        # 可以根据具体政策进行调整
        return self.calculate_requested_refund()

class ReturnPolicy(models.Model):
    """退货政策"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('政策名称', max_length=100)
    is_default = models.BooleanField('默认政策', default=False)
    
    # 时间限制
    return_period_days = models.IntegerField('退货期限(天)', default=30)
    allow_partial_returns = models.BooleanField('允许部分退货', default=True)
    
    # 条件限制
    require_original_packaging = models.BooleanField('需要原包装', default=False)
    require_tags_attached = models.BooleanField('需要标签完好', default=False)
    allow_used_items = models.BooleanField('允许使用后退货', default=False)
    
    # 费用政策
    customer_pays_return_shipping = models.BooleanField('客户承担退货运费', default=False)
    restocking_fee_percentage = models.DecimalField('重新上架费比例', max_digits=5, decimal_places=2, 
                                                   default=0, validators=[MinValueValidator(0)])
    
    # 退款选项
    refund_methods = models.JSONField('退款方式', default=list)  # ['original', 'store_credit', 'exchange']
    exchange_timeframe_days = models.IntegerField('换货期限(天)', default=14)
    
    # 排除商品
    excluded_categories = models.ManyToManyField('products.ProductCategory', blank=True, 
                                                related_name='excluded_from_returns')
    excluded_products = models.ManyToManyField('products.Product', blank=True, 
                                              related_name='excluded_from_returns')
    
    # 备注
    notes = models.TextField('政策说明', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '退货政策'
        verbose_name_plural = '退货政策'
    
    def __str__(self):
        return self.name
    
    def is_product_eligible(self, product, purchase_date):
        """检查商品是否符合退货条件"""
        from django.utils import timezone
        
        # 检查是否在排除列表中
        if product in self.excluded_products.all():
            return False, '该商品不支持退货'
        
        if product.category in self.excluded_categories.all():
            return False, '该分类商品不支持退货'
        
        # 检查是否在退货期限内
        days_since_purchase = (timezone.now().date() - purchase_date.date()).days
        if days_since_purchase > self.return_period_days:
            return False, f'已超过{self.return_period_days}天退货期限'
        
        return True, '符合退货条件'
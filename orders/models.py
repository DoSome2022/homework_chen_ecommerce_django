from django.db import models
from django.core.validators import MinValueValidator
import uuid

class ShoppingCart(models.Model):
    """购物车"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField('accounts.Customer', on_delete=models.CASCADE, 
                                   related_name='shopping_cart')
    
    # 统计信息
    item_count = models.IntegerField('商品数量', default=0)
    total_quantity = models.IntegerField('总数量', default=0)
    subtotal = models.DecimalField('小计', max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField('税费', max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField('运费', max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField('总计', max_digits=12, decimal_places=2, default=0)
    
    # 优惠信息
    discount_amount = models.DecimalField('折扣金额', max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField('优惠券代码', max_length=50, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '购物车'
        verbose_name_plural = '购物车'
    
    def __str__(self):
        return f'{self.customer.user.username}的购物车'
    
    def calculate_totals(self):
        """计算购物车总额"""
        items = self.cart_items.all()
        
        self.item_count = items.count()
        self.total_quantity = sum(item.quantity for item in items)
        self.subtotal = sum(item.total_price for item in items)
        
        # 计算税费（简化示例）
        self.tax = self.subtotal * 0.1  # 10% 税率
        
        # 计算运费（简化示例）
        if self.subtotal >= 100:
            self.shipping_cost = 0
        else:
            self.shipping_cost = 10
        
        # 计算总计
        self.total = self.subtotal + self.tax + self.shipping_cost - self.discount_amount
        
        self.save()
    
    def clear_cart(self):
        """清空购物车"""
        self.cart_items.all().delete()
        self.item_count = 0
        self.total_quantity = 0
        self.subtotal = 0
        self.tax = 0
        self.shipping_cost = 0
        self.total = 0
        self.discount_amount = 0
        self.coupon_code = ''
        self.save()
    
    def apply_coupon(self, coupon_code):
        """应用优惠券"""
        from promotions.models import Coupon
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            if coupon.is_valid_for_cart(self):
                self.coupon_code = coupon_code
                self.discount_amount = coupon.calculate_discount(self.subtotal)
                self.calculate_totals()
                return True, '优惠券应用成功'
        except Coupon.DoesNotExist:
            pass
        return False, '优惠券无效或已过期'

class CartItem(models.Model):
    """购物车项目"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    # variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, 
    #                           null=True, blank=True)
    
    quantity = models.IntegerField('数量', default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('总价', max_digits=12, decimal_places=2)
    
    added_at = models.DateTimeField('添加时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '购物车项目'
        verbose_name_plural = '购物车项目'
        # unique_together = ['cart', 'product', 'variant']
    
    def __str__(self):
        product_name = self.variant.name if self.variant else self.product.name
        return f'{product_name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        # 计算价格
        if self.variant:
            self.unit_price = self.variant.final_price
        else:
            self.unit_price = self.product.price
        
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        
        # 更新购物车总额
        self.cart.calculate_totals()
    
    def delete(self, *args, **kwargs):
        cart = self.cart
        super().delete(*args, **kwargs)
        cart.calculate_totals()

class Order(models.Model):
    """订单"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('pending', '待付款'),
        ('payment_review', '支付审核'),
        ('processing', '处理中'),
        ('on_hold', '暂停'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
        ('failed', '失败'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', '待支付'),
        ('authorized', '已授权'),
        ('paid', '已支付'),
        ('partially_paid', '部分支付'),
        ('refunded', '已退款'),
        ('voided', '已作废'),
    ]
    
    FULFILLMENT_STATUS_CHOICES = [
        ('unfulfilled', '未发货'),
        ('partially_fulfilled', '部分发货'),
        ('fulfilled', '已发货'),
        ('delivered', '已送达'),
        ('returned', '已退回'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField('订单号', max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey('accounts.Customer', on_delete=models.PROTECT, 
                                related_name='orders')
    
    # 订单状态
    status = models.CharField('订单状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField('支付状态', max_length=20, choices=PAYMENT_STATUS_CHOICES, 
                                     default='pending')
    fulfillment_status = models.CharField('发货状态', max_length=20, choices=FULFILLMENT_STATUS_CHOICES, 
                                         default='unfulfilled')
    
    # 金额信息
    subtotal = models.DecimalField('小计', max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField('税费', max_digits=12, decimal_places=2, default=0)
    shipping_amount = models.DecimalField('运费', max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField('折扣金额', max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField('订单总额', max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField('已付金额', max_digits=12, decimal_places=2, default=0)
    refunded_amount = models.DecimalField('退款金额', max_digits=12, decimal_places=2, default=0)
    
    # 支付信息
    payment_method = models.CharField('支付方式', max_length=50, blank=True)
    payment_gateway = models.CharField('支付网关', max_length=50, blank=True)
    payment_transaction_id = models.CharField('支付交易ID', max_length=100, blank=True)
    
    # 配送信息
    shipping_method = models.CharField('配送方式', max_length=100, blank=True)
    shipping_address = models.JSONField('配送地址', default=dict)
    billing_address = models.JSONField('账单地址', default=dict)
    
    # 客户信息
    customer_note = models.TextField('客户备注', blank=True)
    customer_email = models.EmailField('客户邮箱')
    customer_phone = models.CharField('客户电话', max_length=20, blank=True)
    
    # 时间信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    paid_at = models.DateTimeField('支付时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    cancelled_at = models.DateTimeField('取消时间', null=True, blank=True)
    
    # 促销信息
    coupon_code = models.CharField('优惠券代码', max_length=50, blank=True)
    
    # 员工信息
    sales_rep = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                 null=True, blank=True, related_name='assigned_orders')
    
    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['created_at', 'status']),
        ]
    
    def __str__(self):
        return f'{self.order_number} - {self.customer.user.username}'
    
    def generate_order_number(self):
        """生成订单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = Order.objects.filter(
            order_number__startswith=f'ORD{date_str}'
        ).count() + 1
        return f'ORD{date_str}{count:06d}'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # 自动计算总额
        self.calculate_totals()
        
        super().save(*args, **kwargs)
        
        # 更新客户统计信息
        if self.status == 'completed':
            self.update_customer_stats()
    
    def calculate_totals(self):
        """计算订单总额"""
        items = self.order_items.all()
        
        self.subtotal = sum(item.total_price for item in items)
        
        # 应用客户等级折扣
        customer_discount = self.customer.get_discount_rate()
        if customer_discount > 0:
            self.discount_amount = self.subtotal * (customer_discount / 100)
        
        # 计算总额
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_amount - self.discount_amount
        
        # 更新已付金额
        payments = self.payments.filter(status='completed')
        self.paid_amount = sum(payment.amount for payment in payments)
    
    def update_customer_stats(self):
        """更新客户统计信息"""
        self.customer.total_spent += self.total_amount
        self.customer.total_orders += 1
        self.customer.completed_orders += 1
        self.customer.last_purchase_date = self.completed_at
        self.customer.save()
        
        # 增加忠诚度积分（每消费1元获得1积分）
        points = int(self.total_amount)
        self.customer.add_loyalty_points(points, f'订单 {self.order_number}')
    
    def create_from_cart(self, cart):
        """从购物车创建订单"""
        # 复制购物车项目到订单
        for cart_item in cart.cart_items.all():
            OrderItem.objects.create(
                order=self,
                product=cart_item.product,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price
            )
        
        # 复制地址信息
        self.shipping_address = cart.customer.shipping_address[0] if cart.customer.shipping_address else {}
        self.billing_address = cart.customer.billing_address
        
        # 复制促销信息
        if cart.coupon_code:
            self.coupon_code = cart.coupon_code
        
        # 计算总额
        self.calculate_totals()
        self.status = 'pending'
        self.save()
        
        # 清空购物车
        cart.clear_cart()
        
        return self
    
    def allocate_inventory(self):
        """为订单分配库存"""
        success = True
        errors = []
        
        for item in self.order_items.all():
            # 查找可用的库存
            inventory = Inventory.objects.filter(
                product=item.product,
                warehouse__is_active=True,
                available_quantity__gte=item.quantity,
                status='active'
            ).first()
            
            if inventory:
                if inventory.reserve_stock(item.quantity):
                    item.allocated_inventory = inventory
                    item.save()
                else:
                    success = False
                    errors.append(f'{item.product.name}: 库存预留失败')
            else:
                success = False
                errors.append(f'{item.product.name}: 库存不足')
        
        return success, errors
    
    def mark_as_paid(self, payment_method, transaction_id):
        """标记订单为已支付"""
        self.payment_status = 'paid'
        self.status = 'processing'
        self.payment_method = payment_method
        self.payment_transaction_id = transaction_id
        self.paid_at = timezone.now()
        self.save()
        
        # 分配库存
        self.allocate_inventory()
        
        # 触发发货流程
        from shipping.models import Shipment
        Shipment.create_from_order(self)

class OrderItem(models.Model):
    """订单项目"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    # variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, 
    #                           null=True, blank=True)
    
    quantity = models.IntegerField('数量', validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('总价', max_digits=12, decimal_places=2)
    
    # 库存分配
    allocated_inventory = models.ForeignKey('inventory.Inventory', on_delete=models.SET_NULL, 
                                          null=True, blank=True)
    
    # 发货信息
    quantity_shipped = models.IntegerField('已发货数量', default=0)
    quantity_refunded = models.IntegerField('已退款数量', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '订单项目'
        verbose_name_plural = '订单项目'
        ordering = ['order', 'product']
    
    def __str__(self):
        product_name = self.variant.name if self.variant else self.product.name
        return f'{self.order.order_number} - {product_name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        # 计算总价
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
    
    @property
    def product_name(self):
        return self.variant.name if self.variant else self.product.name
    
    @property
    def is_fully_shipped(self):
        return self.quantity_shipped >= self.quantity
    
    @property
    def is_fully_refunded(self):
        return self.quantity_refunded >= self.quantity
    
    def ship_quantity(self, quantity):
        """发货指定数量"""
        if quantity <= self.quantity - self.quantity_shipped:
            self.quantity_shipped += quantity
            
            # 从库存中分配
            if self.allocated_inventory:
                self.allocated_inventory.allocate_stock(quantity)
            
            self.save()
            return True
        return False
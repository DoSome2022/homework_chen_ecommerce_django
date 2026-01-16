from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Promotion(models.Model):
    """促销活动"""
    PROMOTION_TYPES = [
        ('percentage_discount', '百分比折扣'),
        ('fixed_amount_discount', '固定金额折扣'),
        ('buy_x_get_y', '买X送Y'),
        ('bundle', '捆绑销售'),
        ('free_shipping', '免运费'),
        ('gift_with_purchase', '赠品'),
    ]
    
    SCOPE_CHOICES = [
        ('entire_order', '整单'),
        ('specific_products', '指定商品'),
        ('product_category', '商品分类'),
        ('collection', '商品集合'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('促销名称', max_length=200)
    promotion_type = models.CharField('促销类型', max_length=50, choices=PROMOTION_TYPES)
    
    # 折扣配置
    discount_value = models.DecimalField('折扣值', max_digits=10, decimal_places=2, 
                                        null=True, blank=True, validators=[MinValueValidator(0)])
    discount_percentage = models.DecimalField('折扣百分比', max_digits=5, decimal_places=2, 
                                             null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # 范围配置
    scope = models.CharField('适用范围', max_length=50, choices=SCOPE_CHOICES, default='entire_order')
    target_products = models.ManyToManyField('products.Product', blank=True, 
                                            related_name='promotions')
    target_categories = models.ManyToManyField('products.ProductCategory', blank=True, 
                                              related_name='promotions')
    
    # 条件配置
    minimum_purchase_amount = models.DecimalField('最低购买金额', max_digits=10, decimal_places=2, 
                                                 null=True, blank=True, validators=[MinValueValidator(0)])
    minimum_quantity = models.IntegerField('最低购买数量', null=True, blank=True)
    maximum_usage_per_customer = models.IntegerField('每客户最大使用次数', null=True, blank=True)
    
    # 赠品配置
    gift_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='gift_promotions')
    gift_quantity = models.IntegerField('赠品数量', default=1)
    
    # 买X送Y配置
    buy_quantity = models.IntegerField('购买数量', null=True, blank=True)
    get_quantity = models.IntegerField('获得数量', null=True, blank=True)
    get_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='buy_get_promotions')
    
    # 时间配置
    start_date = models.DateTimeField('开始时间')
    end_date = models.DateTimeField('结束时间')
    is_active = models.BooleanField('是否激活', default=True)
    
    # 使用限制
    usage_limit = models.IntegerField('使用次数限制', null=True, blank=True)
    usage_count = models.IntegerField('已使用次数', default=0, validators=[MinValueValidator(0)])
    
    # 优先级
    priority = models.IntegerField('优先级', default=0, 
                                  help_text='数值越大优先级越高')
    
    # 展示信息
    description = models.TextField('描述', blank=True)
    banner_image = models.ImageField('横幅图片', upload_to='promotion_banners/', null=True, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '促销活动'
        verbose_name_plural = '促销活动'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    def is_active_now(self):
        """检查促销是否当前有效"""
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
    def calculate_discount(self, amount, cart_items=None):
        """计算折扣金额"""
        if not self.is_active_now():
            return 0
        
        # 检查条件
        if self.minimum_purchase_amount and amount < self.minimum_purchase_amount:
            return 0
        
        if self.minimum_quantity and cart_items:
            total_quantity = sum(item.quantity for item in cart_items)
            if total_quantity < self.minimum_quantity:
                return 0
        
        # 计算折扣
        if self.promotion_type == 'percentage_discount' and self.discount_percentage:
            return amount * self.discount_percentage / 100
        
        elif self.promotion_type == 'fixed_amount_discount' and self.discount_value:
            return min(self.discount_value, amount)
        
        return 0
    
    def apply_to_cart(self, cart):
        """应用到购物车"""
        if not self.is_active_now():
            return False
        
        # 计算符合条件的商品总额
        eligible_amount = 0
        
        if self.scope == 'entire_order':
            eligible_amount = cart.subtotal
        
        elif self.scope == 'specific_products':
            for item in cart.cart_items.all():
                if item.product in self.target_products.all():
                    eligible_amount += item.total_price
        
        elif self.scope == 'product_category':
            for item in cart.cart_items.all():
                if item.product.category in self.target_categories.all():
                    eligible_amount += item.total_price
        
        # 检查条件
        if self.minimum_purchase_amount and eligible_amount < self.minimum_purchase_amount:
            return False
        
        # 应用折扣
        discount = self.calculate_discount(eligible_amount)
        if discount > 0:
            cart.discount_amount += discount
            cart.calculate_totals()
            
            # 增加使用次数
            self.usage_count += 1
            self.save()
            
            return True
        
        return False

class Coupon(models.Model):
    """优惠券"""
    COUPON_TYPES = [
        ('percentage', '百分比折扣'),
        ('fixed_amount', '固定金额'),
        ('free_shipping', '免运费'),
        ('bogo', '买一送一'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField('优惠码', max_length=50, unique=True)
    coupon_type = models.CharField('优惠券类型', max_length=20, choices=COUPON_TYPES)
    
    # 折扣配置
    discount_value = models.DecimalField('折扣值', max_digits=10, decimal_places=2, 
                                        null=True, blank=True, validators=[MinValueValidator(0)])
    discount_percentage = models.DecimalField('折扣百分比', max_digits=5, decimal_places=2, 
                                             null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # 条件配置
    minimum_purchase_amount = models.DecimalField('最低购买金额', max_digits=10, decimal_places=2, 
                                                 null=True, blank=True, validators=[MinValueValidator(0)])
    maximum_discount_amount = models.DecimalField('最大折扣金额', max_digits=10, decimal_places=2, 
                                                 null=True, blank=True, validators=[MinValueValidator(0)])
    
    # 范围配置
    applicable_products = models.ManyToManyField('products.Product', blank=True, 
                                                related_name='coupons')
    applicable_categories = models.ManyToManyField('products.ProductCategory', blank=True, 
                                                  related_name='coupons')
    
    # 使用限制
    usage_limit = models.IntegerField('使用次数限制', null=True, blank=True)
    usage_per_customer = models.IntegerField('每客户使用次数', default=1)
    usage_count = models.IntegerField('已使用次数', default=0, validators=[MinValueValidator(0)])
    
    # 时间配置
    valid_from = models.DateTimeField('生效时间')
    valid_until = models.DateTimeField('失效时间')
    is_active = models.BooleanField('是否激活', default=True)
    
    # 客户限制
    for_new_customers_only = models.BooleanField('仅限新客户', default=False)
    customer_limit = models.ManyToManyField('accounts.Customer', blank=True, 
                                           related_name='personal_coupons')
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '优惠券'
        verbose_name_plural = '优惠券'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f'{self.code} - {self.get_coupon_type_display()}'
    
    def is_valid(self):
        """检查优惠券是否有效"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if now < self.valid_from or now > self.valid_until:
            return False
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        
        return True
    
    def is_valid_for_cart(self, cart):
        """检查优惠券是否适用于购物车"""
        if not self.is_valid():
            return False
        
        # 检查客户限制
        if self.for_new_customers_only and cart.customer.total_orders > 0:
            return False
        
        if self.customer_limit.exists() and cart.customer not in self.customer_limit.all():
            return False
        
        # 检查金额条件
        if self.minimum_purchase_amount and cart.subtotal < self.minimum_purchase_amount:
            return False
        
        # 检查商品范围
        if self.applicable_products.exists() or self.applicable_categories.exists():
            has_eligible_product = False
            
            for item in cart.cart_items.all():
                if (self.applicable_products.filter(id=item.product.id).exists() or
                    self.applicable_categories.filter(id=item.product.category.id).exists()):
                    has_eligible_product = True
                    break
            
            if not has_eligible_product:
                return False
        
        return True
    
    def is_valid_for_customer(self, customer):
        """检查优惠券是否适用于客户"""
        if not self.is_valid():
            return False
        
        # 检查客户限制
        if self.for_new_customers_only and customer.total_orders > 0:
            return False
        
        if self.customer_limit.exists() and customer not in self.customer_limit.all():
            return False
        
        # 检查使用次数限制
        usage_by_customer = CouponUsage.objects.filter(
            coupon=self,
            customer=customer
        ).count()
        
        if usage_by_customer >= self.usage_per_customer:
            return False
        
        return True
    
    def calculate_discount(self, amount):
        """计算折扣金额"""
        if self.coupon_type == 'percentage':
            discount = amount * self.discount_percentage / 100
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
            return discount
        
        elif self.coupon_type == 'fixed_amount':
            return min(self.discount_value, amount)
        
        elif self.coupon_type == 'free_shipping':
            return 0  # 运费在购物车计算中单独处理
        
        return 0
    
    def apply_to_order(self, order):
        """应用到订单"""
        if not self.is_valid_for_customer(order.customer):
            return False, '优惠券不适用于此客户'
        
        # 检查条件
        if self.minimum_purchase_amount and order.subtotal < self.minimum_purchase_amount:
            return False, '未达到最低购买金额'
        
        # 计算折扣
        discount = self.calculate_discount(order.subtotal)
        
        if discount > 0:
            order.discount_amount += discount
            order.coupon_code = self.code
            order.calculate_totals()
            order.save()
            
            # 记录使用
            CouponUsage.objects.create(
                coupon=self,
                customer=order.customer,
                order=order,
                discount_amount=discount
            )
            
            # 增加使用次数
            self.usage_count += 1
            self.save()
            
            return True, f'优惠券已应用，折扣: {discount}'
        
        return False, '无法应用优惠券'

class CouponUsage(models.Model):
    """优惠券使用记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, 
                                related_name='coupon_usages')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, 
                             related_name='coupon_usages')
    
    discount_amount = models.DecimalField('折扣金额', max_digits=10, decimal_places=2)
    used_at = models.DateTimeField('使用时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '优惠券使用记录'
        verbose_name_plural = '优惠券使用记录'
        ordering = ['-used_at']
        unique_together = ['coupon', 'order']
    
    def __str__(self):
        return f'{self.coupon.code} - {self.order.order_number}'

class FlashSale(models.Model):
    """限时抢购"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('抢购名称', max_length=200)
    
    # 时间配置
    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间')
    is_active = models.BooleanField('是否激活', default=True)
    
    # 商品配置
    products = models.ManyToManyField('products.Product', through='FlashSaleProduct')
    
    # 限制配置
    purchase_limit_per_customer = models.IntegerField('每客户限购数量', default=1)
    total_quantity_limit = models.IntegerField('总数量限制', null=True, blank=True)
    
    # 展示配置
    banner_image = models.ImageField('横幅图片', upload_to='flash_sale_banners/', null=True, blank=True)
    description = models.TextField('描述', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '限时抢购'
        verbose_name_plural = '限时抢购'
        ordering = ['-start_time']
    
    def __str__(self):
        return self.name
    
    def is_active_now(self):
        """检查是否正在进行"""
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time
    
    def get_remaining_quantity(self, product):
        """获取剩余数量"""
        try:
            flash_sale_product = self.flash_sale_products.get(product=product)
            sold_quantity = flash_sale_product.sold_quantity
            limit = flash_sale_product.quantity_limit
            
            if limit:
                return max(0, limit - sold_quantity)
            return None  # 无限制
        except FlashSaleProduct.DoesNotExist:
            return 0

class FlashSaleProduct(models.Model):
    """限时抢购商品"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flash_sale = models.ForeignKey(FlashSale, on_delete=models.CASCADE, related_name='flash_sale_products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='flash_sales')
    
    # 价格配置
    sale_price = models.DecimalField('抢购价格', max_digits=10, decimal_places=2, 
                                    validators=[MinValueValidator(0)])
    
    # 数量配置
    quantity_limit = models.IntegerField('数量限制', null=True, blank=True)
    sold_quantity = models.IntegerField('已售数量', default=0, validators=[MinValueValidator(0)])
    
    # 状态
    is_active = models.BooleanField('是否激活', default=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '限时抢购商品'
        verbose_name_plural = '限时抢购商品'
        unique_together = ['flash_sale', 'product']
    
    def __str__(self):
        return f'{self.product.name} - {self.sale_price}'
    
    @property
    def is_available(self):
        """检查是否还有库存"""
        if not self.is_active:
            return False
        
        if not self.flash_sale.is_active_now():
            return False
        
        if self.quantity_limit and self.sold_quantity >= self.quantity_limit:
            return False
        
        return True
    
    def reserve_quantity(self, quantity):
        """预留数量"""
        if self.is_available and quantity <= self.get_available_quantity():
            self.sold_quantity += quantity
            self.save()
            return True
        return False
    
    def get_available_quantity(self):
        """获取可用数量"""
        if self.quantity_limit:
            return max(0, self.quantity_limit - self.sold_quantity)
        return 999999  # 无限制时返回一个大数
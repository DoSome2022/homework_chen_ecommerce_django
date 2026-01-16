from django.db import models
from django.core.validators import MinValueValidator
import uuid

class PaymentMethod(models.Model):
    """支付方式"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('支付方式名称', max_length=100)
    code = models.CharField('支付方式代码', max_length=50, unique=True)
    
    # 支付方式类型
    payment_type = models.CharField('支付类型', max_length=50, 
                                   choices=[('card', '银行卡'), ('digital_wallet', '电子钱包'), 
                                           ('bank_transfer', '银行转账'), ('cod', '货到付款')])
    
    # 配置信息
    is_active = models.BooleanField('是否激活', default=True)
    supports_refund = models.BooleanField('支持退款', default=True)
    processing_fee_percentage = models.DecimalField('手续费比例', max_digits=5, decimal_places=2, 
                                                   default=0, validators=[MinValueValidator(0)])
    processing_fee_fixed = models.DecimalField('固定手续费', max_digits=10, decimal_places=2, 
                                              default=0, validators=[MinValueValidator(0)])
    
    # 网关配置
    gateway_name = models.CharField('支付网关', max_length=100, blank=True)
    gateway_config = models.JSONField('网关配置', default=dict)
    
    # 显示设置
    display_order = models.IntegerField('显示顺序', default=0)
    icon = models.CharField('图标类名', max_length=100, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '支付方式'
        verbose_name_plural = '支付方式'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    def calculate_processing_fee(self, amount):
        """计算手续费"""
        fee = (amount * self.processing_fee_percentage / 100) + self.processing_fee_fixed
        return round(fee, 2)

class Payment(models.Model):
    """支付记录"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('authorized', '已授权'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
        ('partially_refunded', '部分退款'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_number = models.CharField('支付单号', max_length=50, unique=True)
    
    # 关联订单
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    
    # 支付信息
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, 
                                      related_name='payments')
    amount = models.DecimalField('支付金额', max_digits=12, decimal_places=2, 
                                validators=[MinValueValidator(0.01)])
    currency = models.CharField('货币代码', max_length=3, default='CNY')
    
    # 状态信息
    status = models.CharField('支付状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_fee = models.DecimalField('手续费', max_digits=10, decimal_places=2, default=0)
    
    # 网关信息
    gateway_transaction_id = models.CharField('网关交易ID', max_length=100, blank=True)
    gateway_response = models.JSONField('网关响应', default=dict)
    gateway_error = models.TextField('网关错误', blank=True)
    
    # 客户信息
    payer_name = models.CharField('付款人姓名', max_length=100, blank=True)
    payer_email = models.EmailField('付款人邮箱', blank=True)
    payer_phone = models.CharField('付款人电话', max_length=20, blank=True)
    
    # 时间信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    authorized_at = models.DateTimeField('授权时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    refunded_at = models.DateTimeField('退款时间', null=True, blank=True)
    
    class Meta:
        verbose_name = '支付记录'
        verbose_name_plural = '支付记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['order', 'status']),
        ]
    
    def __str__(self):
        return f'{self.payment_number} - {self.amount} {self.currency}'
    
    def generate_payment_number(self):
        """生成支付单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = Payment.objects.filter(
            payment_number__startswith=f'PAY{date_str}'
        ).count() + 1
        return f'PAY{date_str}{count:06d}'
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        # 计算手续费
        if self.payment_method:
            self.processing_fee = self.payment_method.calculate_processing_fee(self.amount)
        
        super().save(*args, **kwargs)
    
    def process_payment(self):
        """处理支付"""
        from .gateways import get_payment_gateway
        
        try:
            gateway = get_payment_gateway(self.payment_method.gateway_name)
            
            # 调用网关进行支付
            result = gateway.process_payment(
                amount=float(self.amount),
                order_number=self.order.order_number,
                customer_email=self.order.customer_email,
                customer_phone=self.order.customer_phone
            )
            
            if result['success']:
                self.status = 'completed' if result.get('captured', True) else 'authorized'
                self.gateway_transaction_id = result.get('transaction_id', '')
                self.gateway_response = result.get('response', {})
                self.completed_at = timezone.now()
                
                # 更新订单支付状态
                self.order.payment_status = 'paid'
                self.order.paid_amount += self.amount
                self.order.save()
                
                # 如果支付完成，触发订单处理
                if self.status == 'completed':
                    self.order.mark_as_paid(
                        payment_method=self.payment_method.name,
                        transaction_id=self.gateway_transaction_id
                    )
            else:
                self.status = 'failed'
                self.gateway_error = result.get('error_message', '支付失败')
            
            self.save()
            return result['success'], result.get('error_message', '')
            
        except Exception as e:
            self.status = 'failed'
            self.gateway_error = str(e)
            self.save()
            return False, str(e)
    
    def refund(self, amount=None):
        """退款"""
        if amount is None:
            amount = self.amount
        
        if amount > self.amount:
            return False, '退款金额不能超过支付金额'
        
        if not self.payment_method.supports_refund:
            return False, '该支付方式不支持退款'
        
        from .gateways import get_payment_gateway
        
        try:
            gateway = get_payment_gateway(self.payment_method.gateway_name)
            
            result = gateway.refund_payment(
                transaction_id=self.gateway_transaction_id,
                amount=float(amount)
            )
            
            if result['success']:
                # 创建退款记录
                Refund.objects.create(
                    payment=self,
                    amount=amount,
                    reason=result.get('reason', '客户退款'),
                    gateway_transaction_id=result.get('refund_id', ''),
                    gateway_response=result.get('response', {})
                )
                
                # 更新支付状态
                if amount == self.amount:
                    self.status = 'refunded'
                else:
                    self.status = 'partially_refunded'
                
                self.refunded_at = timezone.now()
                self.save()
                
                # 更新订单退款金额
                self.order.refunded_amount += amount
                self.order.save()
                
                return True, '退款成功'
            else:
                return False, result.get('error_message', '退款失败')
                
        except Exception as e:
            return False, str(e)

class Refund(models.Model):
    """退款记录"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund_number = models.CharField('退款单号', max_length=50, unique=True)
    
    # 关联信息
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='refunds')
    
    # 退款信息
    amount = models.DecimalField('退款金额', max_digits=12, decimal_places=2, 
                                validators=[MinValueValidator(0.01)])
    currency = models.CharField('货币代码', max_length=3, default='CNY')
    reason = models.TextField('退款原因')
    
    # 状态信息
    status = models.CharField('退款状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 网关信息
    gateway_transaction_id = models.CharField('网关交易ID', max_length=100, blank=True)
    gateway_response = models.JSONField('网关响应', default=dict)
    gateway_error = models.TextField('网关错误', blank=True)
    
    # 处理信息
    processed_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='processed_refunds')
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    class Meta:
        verbose_name = '退款记录'
        verbose_name_plural = '退款记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.refund_number} - {self.amount} {self.currency}'
    
    def generate_refund_number(self):
        """生成退款单号"""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        count = Refund.objects.filter(
            refund_number__startswith=f'REF{date_str}'
        ).count() + 1
        return f'REF{date_str}{count:06d}'
    
    def save(self, *args, **kwargs):
        if not self.refund_number:
            self.refund_number = self.generate_refund_number()
        super().save(*args, **kwargs)

class PaymentGatewayConfig(models.Model):
    """支付网关配置"""
    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('alipay', '支付宝'),
        ('wechat_pay', '微信支付'),
        ('bank_transfer', '银行转账'),
        ('cash_on_delivery', '货到付款'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gateway = models.CharField('支付网关', max_length=50, choices=GATEWAY_CHOICES, unique=True)
    is_active = models.BooleanField('是否激活', default=True)
    
    # API 配置
    api_key = models.CharField('API密钥', max_length=255, blank=True)
    api_secret = models.CharField('API密钥', max_length=255, blank=True)
    webhook_secret = models.CharField('Webhook密钥', max_length=255, blank=True)
    
    # 环境配置
    environment = models.CharField('环境', max_length=20, 
                                  choices=[('sandbox', '沙箱'), ('production', '生产')],
                                  default='sandbox')
    
    # 附加配置
    config = models.JSONField('配置信息', default=dict)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '支付网关配置'
        verbose_name_plural = '支付网关配置'
    
    def __str__(self):
        return self.get_gateway_display()
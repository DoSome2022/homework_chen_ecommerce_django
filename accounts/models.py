from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid

class UserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError('用户必须提供电子邮件地址')
        
        if not username:
            username = email.split('@')[0]
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractUser):
    """自定义用户模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('电子邮件', unique=True)
    phone = models.CharField('电话号码', max_length=20, blank=True)
    avatar = models.ImageField('头像', upload_to='avatars/', null=True, blank=True)
    date_of_birth = models.DateField('出生日期', null=True, blank=True)
    is_email_verified = models.BooleanField('邮箱已验证', default=False)
    email_verified_at = models.DateTimeField('邮箱验证时间', null=True, blank=True)
    
    # 覆盖AbstractUser的字段
    username = models.CharField('用户名', max_length=150, unique=True, db_index=True)
    first_name = models.CharField('名', max_length=150, blank=True)
    last_name = models.CharField('姓', max_length=150, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    last_login = models.DateTimeField('最后登录', null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.username} ({self.email})'
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f'{self.last_name}{self.first_name}'
        return self.username
    
    def verify_email(self):
        self.is_email_verified = True
        self.email_verified_at = timezone.now()
        self.save()

class CustomerLevel(models.Model):
    """客户等级"""
    LEVEL_CHOICES = [
        ('bronze', '青铜会员'),
        ('silver', '白银会员'),
        ('gold', '黄金会员'),
        ('platinum', '白金会员'),
        ('diamond', '钻石会员'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('等级名称', max_length=50)
    level = models.CharField('等级代码', max_length=20, choices=LEVEL_CHOICES, unique=True)
    discount_rate = models.DecimalField('折扣率', max_digits=5, decimal_places=2, 
                                        default=0, validators=[MinValueValidator(0)])
    min_points = models.IntegerField('最小积分', default=0)
    max_points = models.IntegerField('最大积分', null=True, blank=True)
    benefits = models.JSONField('会员权益', default=list)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '客户等级'
        verbose_name_plural = '客户等级'
        ordering = ['min_points']
    
    def __str__(self):
        return f'{self.name} ({self.get_level_display()})'
    
    @classmethod
    def get_level_by_points(cls, points):
        """根据积分获取等级"""
        return cls.objects.filter(
            min_points__lte=points,
            max_points__gte=points if cls.objects.filter(max_points__isnull=False).exists() else None
        ).first() or cls.objects.filter(max_points__isnull=True, min_points__lte=points).first()

class Customer(models.Model):
    """客户信息"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    level = models.ForeignKey(CustomerLevel, on_delete=models.SET_NULL, 
                             null=True, blank=True, related_name='customers')
    loyalty_points = models.IntegerField('忠诚度积分', default=0)
    total_spent = models.DecimalField('总消费金额', max_digits=12, decimal_places=2, default=0)
    joined_date = models.DateTimeField('加入日期', auto_now_add=True)
    last_purchase_date = models.DateTimeField('最后购买日期', null=True, blank=True)
    
    # 地址信息
    shipping_address = models.JSONField('配送地址', default=list)
    billing_address = models.JSONField('账单地址', default=dict)
    
    # 偏好设置
    preferences = models.JSONField('偏好设置', default=dict)
    
    # 统计信息
    total_orders = models.IntegerField('总订单数', default=0)
    completed_orders = models.IntegerField('已完成订单', default=0)
    cancelled_orders = models.IntegerField('已取消订单', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '客户'
        verbose_name_plural = '客户'
        ordering = ['-total_spent']
    
    def __str__(self):
        return f'{self.user.username} - {self.get_level_display()}'
    
    def save(self, *args, **kwargs):
        # 自动更新客户等级
        if self.loyalty_points >= 0:
            new_level = CustomerLevel.get_level_by_points(self.loyalty_points)
            if new_level and new_level != self.level:
                self.level = new_level
        super().save(*args, **kwargs)
    
    def get_level_display(self):
        return self.level.name if self.level else '普通会员'
    
    def get_discount_rate(self):
        return self.level.discount_rate if self.level else 0
    
    def add_loyalty_points(self, points, reason=''):
        """增加忠诚度积分"""
        self.loyalty_points += points
        self.save()
        LoyaltyPointTransaction.objects.create(
            customer=self,
            points=points,
            transaction_type='earn',
            reason=reason
        )
    
    def deduct_loyalty_points(self, points, reason=''):
        """扣除忠诚度积分"""
        if self.loyalty_points >= points:
            self.loyalty_points -= points
            self.save()
            LoyaltyPointTransaction.objects.create(
                customer=self,
                points=points,
                transaction_type='deduct',
                reason=reason
            )
            return True
        return False

class Staff(models.Model):
    """员工信息"""
    DEPARTMENT_CHOICES = [
        ('warehouse', '仓库'),
        ('sales', '销售'),
        ('customer_service', '客服'),
        ('management', '管理'),
        ('it', 'IT'),
        ('finance', '财务'),
        ('marketing', '市场'),
    ]
    
    ROLE_CHOICES = [
        ('staff', '员工'),
        ('supervisor', '主管'),
        ('manager', '经理'),
        ('director', '总监'),
        ('admin', '管理员'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField('员工编号', max_length=50, unique=True)
    department = models.CharField('部门', max_length=50, choices=DEPARTMENT_CHOICES)
    role = models.CharField('角色', max_length=50, choices=ROLE_CHOICES, default='staff')
    hire_date = models.DateField('入职日期')
    salary = models.DecimalField('薪资', max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField('在职状态', default=True)
    
    # 权限配置
    permissions = models.JSONField('权限配置', default=dict)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '员工'
        verbose_name_plural = '员工'
        ordering = ['department', 'role']
    
    def __str__(self):
        return f'{self.user.username} - {self.get_department_display()} - {self.get_role_display()}'
    
    def has_permission(self, permission_key):
        """检查员工是否有特定权限"""
        return self.permissions.get(permission_key, False)

class LoyaltyPointTransaction(models.Model):
    """忠诚度积分交易记录"""
    TRANSACTION_TYPES = [
        ('earn', '获得'),
        ('deduct', '扣除'),
        ('expire', '过期'),
        ('adjust', '调整'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='point_transactions')
    points = models.IntegerField('积分数量')
    transaction_type = models.CharField('交易类型', max_length=20, choices=TRANSACTION_TYPES)
    reason = models.CharField('原因', max_length=255, blank=True)
    reference_id = models.CharField('参考ID', max_length=100, blank=True)
    expiry_date = models.DateField('过期日期', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '积分交易记录'
        verbose_name_plural = '积分交易记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.customer.user.username} - {self.get_transaction_type_display()} {self.points} points'
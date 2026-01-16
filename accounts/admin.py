from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Customer, Staff, CustomerLevel, LoyaltyPointTransaction

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """自定义用户管理界面"""
    list_display = ('username', 'email', 'phone', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {'fields': ('email', 'phone', 'first_name', 'last_name', 'avatar', 'date_of_birth')}),
        (_('权限'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('重要日期'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2'),
        }),
    )
    
    def get_inline_instances(self, request, obj=None):
        """动态显示内联模型"""
        if obj:
            if hasattr(obj, 'customer_profile'):
                return [CustomerInline(self.model, self.admin_site)]
            elif hasattr(obj, 'staff_profile'):
                return [StaffInline(self.model, self.admin_site)]
        return []

class CustomerInline(admin.StackedInline):
    """客户信息内联"""
    model = Customer
    can_delete = False
    verbose_name_plural = '客户信息'
    fields = ('level', 'loyalty_points', 'total_spent', 'total_orders')
    readonly_fields = ('loyalty_points', 'total_spent', 'total_orders')

class StaffInline(admin.StackedInline):
    """员工信息内联"""
    model = Staff
    can_delete = False
    verbose_name_plural = '员工信息'
    fields = ('employee_id', 'department', 'role', 'hire_date', 'is_active')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """客户管理"""
    list_display = ('user', 'level', 'loyalty_points', 'total_spent', 'total_orders', 'joined_date')
    list_filter = ('level', 'joined_date')
    search_fields = ('user__username', 'user__email', 'user__phone')
    readonly_fields = ('joined_date', 'last_purchase_date')
    
    fieldsets = (
        (_('基本信息'), {
            'fields': ('user', 'level', 'loyalty_points', 'total_spent')
        }),
        (_('统计信息'), {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders', 'last_purchase_date')
        }),
        (_('地址信息'), {
            'fields': ('shipping_address', 'billing_address', 'preferences')
        }),
    )

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """员工管理"""
    list_display = ('user', 'employee_id', 'department', 'role', 'hire_date', 'is_active')
    list_filter = ('department', 'role', 'is_active')
    search_fields = ('user__username', 'user__email', 'employee_id')
    
    fieldsets = (
        (_('基本信息'), {
            'fields': ('user', 'employee_id', 'department', 'role')
        }),
        (_('雇佣信息'), {
            'fields': ('hire_date', 'salary', 'is_active')
        }),
        (_('权限配置'), {
            'fields': ('permissions',),
            'description': _('JSON格式的权限配置')
        }),
    )

@admin.register(CustomerLevel)
class CustomerLevelAdmin(admin.ModelAdmin):
    """客户等级管理"""
    list_display = ('name', 'level', 'discount_rate', 'min_points', 'max_points')
    list_filter = ('level',)
    search_fields = ('name', 'level')
    
    fieldsets = (
        (_('等级信息'), {
            'fields': ('name', 'level', 'discount_rate')
        }),
        (_('积分范围'), {
            'fields': ('min_points', 'max_points')
        }),
        (_('会员权益'), {
            'fields': ('benefits',),
            'description': _('JSON格式的权益列表')
        }),
    )

@admin.register(LoyaltyPointTransaction)
class LoyaltyPointTransactionAdmin(admin.ModelAdmin):
    """积分交易记录管理"""
    list_display = ('customer', 'points', 'transaction_type', 'reason', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('customer__user__username', 'reason', 'reference_id')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        (_('交易信息'), {
            'fields': ('customer', 'points', 'transaction_type', 'reason')
        }),
        (_('参考信息'), {
            'fields': ('reference_id', 'expiry_date')
        }),
    )
# accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db import transaction
import json

from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    CustomerProfileForm, StaffProfileForm, ChangePasswordForm
)
from .models import User, Customer, Staff, CustomerLevel
from .decorators import customer_required, staff_required, admin_required

# ============ 辅助函数和装饰器 ============

class CustomLoginView(LoginView):
    """自定义登录视图"""
    template_name = 'accounts/login.html'
    form_class = UserLoginForm
    redirect_authenticated_user = True  # 如果用户已经登录，重定向到其他页面


    def get_success_url(self):
        next_url = self.request.GET.get('next', '')
        if next_url:
            return next_url
                
        user = self.request.user
        
        # 根据用户类型重定向到不同页面
        if hasattr(user, 'staff_profile'):
            return reverse_lazy('accounts:staff_dashboard')
        elif hasattr(user, 'customer_profile'):
            return reverse_lazy('accounts:customer_dashboard')
        else:
            return reverse_lazy('home')
    
    def form_valid(self, form):
        messages.success(self.request, '登录成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, '登入失敗，請檢查您的使用者名稱和密碼。')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加额外上下文
        context['page_title'] = '倉儲管理系統 - 登入'
        return context

class CustomLogoutView(LogoutView):
    """自定义登出视图"""
    next_page = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, '您已成功登出')
        return super().dispatch(request, *args, **kwargs)

# ============ 用户注册 ============

class RegisterView(CreateView):
    """用户注册视图"""
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    @transaction.atomic
    def form_valid(self, form):
        # 创建用户
        user = form.save()
        
        # 默认创建客户资料
        Customer.objects.create(user=user)
        
        messages.success(self.request, '注册成功！请登录您的账户。')
        return redirect(self.success_url)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '用户注册'
        return context

# ============ 客户相关视图 ============

@method_decorator([login_required, customer_required], name='dispatch')
class CustomerDashboardView(DetailView):
    """客户仪表板"""
    model = Customer
    template_name = 'accounts/customer_dashboard.html'
    context_object_name = 'customer'
    
    def get_object(self):
        return get_object_or_404(Customer, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        
        # 获取客户等级信息
        context['level'] = customer.get_level_display()
        context['discount_rate'] = customer.get_discount_rate()
        
        # 获取最近的积分交易
        context['recent_transactions'] = customer.point_transactions.all()[:10]
        
        # 计算下一等级信息
        next_level = CustomerLevel.objects.filter(
            min_points__gt=customer.loyalty_points
        ).order_by('min_points').first()
        context['next_level'] = next_level
        if next_level:
            context['points_needed'] = next_level.min_points - customer.loyalty_points
        
        return context

@method_decorator([login_required, customer_required], name='dispatch')
class CustomerProfileView(UpdateView):
    """客户资料编辑"""
    model = Customer
    form_class = CustomerProfileForm
    template_name = 'accounts/customer_profile.html'
    success_url = reverse_lazy('accounts:customer_dashboard')
    
    def get_object(self):
        return get_object_or_404(Customer, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_form'] = UserProfileForm(instance=self.request.user)
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        # 同时更新用户信息
        user_form = UserProfileForm(self.request.POST, self.request.FILES, instance=self.request.user)
        if user_form.is_valid():
            user_form.save()
        
        messages.success(self.request, '资料更新成功！')
        return super().form_valid(form)

@login_required
@customer_required
def change_password_view(request):
    """修改密码视图"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            update_session_auth_hash(request, user)  # 保持用户登录状态
            messages.success(request, '密码修改成功！')
            return redirect('accounts:customer_dashboard')
    else:
        form = ChangePasswordForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

# ============ 员工相关视图 ============

@method_decorator([login_required, staff_required], name='dispatch')
class StaffDashboardView(DetailView):
    """员工仪表板"""
    model = Staff
    template_name = 'accounts/staff_dashboard.html'
    context_object_name = 'staff'
    
    def get_object(self):
        return get_object_or_404(Staff, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 根据部门显示不同的统计信息
        staff = self.object
        
        # 可以在这里添加部门特定的统计信息
        context['department'] = staff.get_department_display()
        context['role'] = staff.get_role_display()
        
        return context

@method_decorator([login_required, staff_required], name='dispatch')
class StaffProfileView(UpdateView):
    """员工资料编辑"""
    model = Staff
    form_class = StaffProfileForm
    template_name = 'accounts/staff_profile.html'
    success_url = reverse_lazy('accounts:staff_dashboard')
    
    def get_object(self):
        return get_object_or_404(Staff, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_form'] = UserProfileForm(instance=self.request.user)
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        # 同时更新用户信息
        user_form = UserProfileForm(self.request.POST, self.request.FILES, instance=self.request.user)
        if user_form.is_valid():
            user_form.save()
        
        messages.success(self.request, '资料更新成功！')
        return super().form_valid(form)

# ============ 管理员视图 ============

@method_decorator([login_required, admin_required], name='dispatch')
class UserListView(ListView):
    """用户列表（管理员）"""
    model = User
    template_name = 'accounts/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # 搜索功能
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search)
            )
        
        # 过滤功能
        user_type = self.request.GET.get('type', '')
        if user_type == 'customer':
            queryset = queryset.filter(customer_profile__isnull=False)
        elif user_type == 'staff':
            queryset = queryset.filter(staff_profile__isnull=False)
        elif user_type == 'admin':
            queryset = queryset.filter(is_staff=True)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['user_type'] = self.request.GET.get('type', '')
        return context

@method_decorator([login_required, admin_required], name='dispatch')
class UserDetailView(DetailView):
    """用户详情（管理员）"""
    model = User
    template_name = 'accounts/admin/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # 获取用户类型特定的信息
        if hasattr(user, 'customer_profile'):
            context['customer'] = user.customer_profile
        if hasattr(user, 'staff_profile'):
            context['staff'] = user.staff_profile
        
        return context

@login_required
@admin_required
def toggle_user_status(request, user_id):
    """切换用户激活状态"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        
        action = '激活' if user.is_active else '禁用'
        messages.success(request, f'用户 {user.username} 已{action}')
    
    return redirect('accounts:user_detail', pk=user_id)

@method_decorator([login_required, admin_required], name='dispatch')
class CustomerLevelListView(ListView):
    """客户等级列表"""
    model = CustomerLevel
    template_name = 'accounts/admin/customer_level_list.html'
    context_object_name = 'levels'
    
    def get_queryset(self):
        return CustomerLevel.objects.all().order_by('min_points')

@method_decorator([login_required, admin_required], name='dispatch')
class CustomerLevelCreateView(CreateView):
    """创建客户等级"""
    model = CustomerLevel
    template_name = 'accounts/admin/customer_level_form.html'
    fields = ['name', 'level', 'discount_rate', 'min_points', 'max_points', 'benefits']
    success_url = reverse_lazy('accounts:customer_level_list')
    
    def form_valid(self, form):
        messages.success(self.request, '客户等级创建成功！')
        return super().form_valid(form)

@method_decorator([login_required, admin_required], name='dispatch')
class CustomerLevelUpdateView(UpdateView):
    """编辑客户等级"""
    model = CustomerLevel
    template_name = 'accounts/admin/customer_level_form.html'
    fields = ['name', 'level', 'discount_rate', 'min_points', 'max_points', 'benefits']
    success_url = reverse_lazy('accounts:customer_level_list')
    
    def form_valid(self, form):
        messages.success(self.request, '客户等级更新成功！')
        return super().form_valid(form)

@login_required
@admin_required
def create_staff(request, user_id):
    """将普通用户提升为员工"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = StaffProfileForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.user = user
            staff.save()
            
            # 赋予员工权限
            user.is_staff = True
            user.save()
            
            messages.success(request, f'已将用户 {user.username} 设为员工')
            return redirect('accounts:user_detail', pk=user_id)
    else:
        form = StaffProfileForm()
    
    return render(request, 'accounts/admin/create_staff.html', {
        'form': form,
        'user': user
    })

# ============ 通用视图 ============

def home_view(request):
    """首页"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'staff_profile'):
            return redirect('accounts:staff_dashboard')
        elif hasattr(request.user, 'customer_profile'):
            return redirect('accounts:customer_dashboard')
    
    return render(request, 'accounts/home.html')
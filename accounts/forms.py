from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, Customer, Staff

class UserRegistrationForm(UserCreationForm):
    """用户注册表单"""
    email = forms.EmailField(
        label='电子邮件',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '请输入邮箱'})
    )
    username = forms.CharField(
        label='用户名',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入用户名'})
    )
    phone = forms.CharField(
        label='手机号码',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入手机号'})
    )
    
    class Meta:
        model = User
        fields = ['email', 'username', 'phone', 'password1', 'password2']
        widgets = {
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请输入密码'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请确认密码'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('该邮箱已被注册')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('该用户名已被使用')
        return username

class UserLoginForm(AuthenticationForm):
    """用户登录表单"""
    username = forms.CharField(
        label='用户名或邮箱',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '用户名或邮箱'})
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请输入密码'})
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        # 检查是否是邮箱
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                username = user.username
                self.cleaned_data['username'] = username
            except User.DoesNotExist:
                raise ValidationError('用户不存在')
        
        return super().clean()

class UserProfileForm(forms.ModelForm):
    """用户资料编辑表单"""
    date_of_birth = forms.DateField(
        label='出生日期',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class CustomerProfileForm(forms.ModelForm):
    """客户资料表单"""
    class Meta:
        model = Customer
        fields = ['shipping_address', 'billing_address', 'preferences']
        widgets = {
            'shipping_address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '请输入配送地址，支持多个地址，JSON格式'
            }),
            'billing_address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '请输入账单地址，JSON格式'
            }),
            'preferences': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '偏好设置，JSON格式'
            }),
        }

class StaffProfileForm(forms.ModelForm):
    """员工资料表单"""
    hire_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    class Meta:
        model = Staff
        fields = ['employee_id', 'department', 'role', 'hire_date', 'salary', 'permissions']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'permissions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ChangePasswordForm(forms.Form):
    """修改密码表单"""
    old_password = forms.CharField(
        label='原密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError('原密码错误')
        return old_password
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('两次输入的新密码不一致')
        return password2
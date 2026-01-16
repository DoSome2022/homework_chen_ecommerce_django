from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def customer_required(view_func):
    """要求用户必须是客户"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not hasattr(request.user, 'customer_profile'):
            raise PermissionDenied("此页面仅对客户开放")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def staff_required(view_func):
    """要求用户必须是员工"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not (request.user.is_staff and hasattr(request.user, 'staff_profile')):
            raise PermissionDenied("此页面仅对员工开放")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """要求用户必须是管理员"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not (request.user.is_staff and request.user.is_superuser):
            raise PermissionDenied("此页面仅对管理员开放")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_permission(permission_key):
    """要求特定权限"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if not hasattr(request.user, 'staff_profile'):
                raise PermissionDenied("需要员工权限")
            
            staff = request.user.staff_profile
            if not staff.has_permission(permission_key):
                raise PermissionDenied(f"需要权限: {permission_key}")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
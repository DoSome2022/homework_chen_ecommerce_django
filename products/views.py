# products/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from .models import Product, ProductCategory, ProductImage, ProductReview, ProductAttributeValue
from .forms import ProductForm, ProductCategoryForm, ProductSearchForm, ProductReviewForm
from accounts.decorators import staff_required, admin_required


# ============ 前台视图 ============

class ProductListView(ListView):
    """产品列表页"""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        
        # 处理搜索表单
        form = ProductSearchForm(self.request.GET)
        
        if form.is_valid():
            # 关键词搜索
            search_query = form.cleaned_data.get('q')
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(sku__icontains=search_query) |
                    Q(tags__icontains=search_query)
                )
            
            # 分类筛选
            category = form.cleaned_data.get('category')
            if category:
                # 包括子分类
                category_ids = [category.id] + [cat.id for cat in category.get_descendants()]
                queryset = queryset.filter(category_id__in=category_ids)
            
            # 价格范围筛选
            min_price = form.cleaned_data.get('min_price')
            max_price = form.cleaned_data.get('max_price')
            
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__lte=max_price)
            
            # 库存筛选
            if form.cleaned_data.get('in_stock'):
                queryset = queryset.filter(stock_quantity__gt=0)
            
            # 特殊标记筛选
            if form.cleaned_data.get('is_featured'):
                queryset = queryset.filter(is_featured=True)
            if form.cleaned_data.get('is_new'):
                queryset = queryset.filter(is_new=True)
        
        # 排序
        sort_by = self.request.GET.get('sort_by', 'newest')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'name_asc':
            queryset = queryset.order_by('name')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-name')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-rating', '-review_count')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-view_count', '-sold_count')
        else:  # newest
            queryset = queryset.order_by('-created_at')
        
        return queryset.select_related('category').prefetch_related('images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ProductSearchForm(self.request.GET)
        
        # 获取热门分类
        context['popular_categories'] = ProductCategory.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count('products')
        ).filter(
            product_count__gt=0
        ).order_by('-product_count')[:8]
        
        # 获取推荐产品
        context['featured_products'] = Product.objects.filter(
            is_active=True, is_featured=True
        )[:8]
        
        # 获取新品
        context['new_products'] = Product.objects.filter(
            is_active=True, is_new=True
        )[:8]
        
        return context


class ProductDetailView(DetailView):
    """产品详情页"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # 增加浏览次数
        product.increment_view_count()
        
        # 获取相关产品
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(
            pk=product.pk
        )[:4]
        
        # 获取评价
        context['reviews'] = ProductReview.objects.filter(
            product=product,
            is_approved=True
        ).select_related('customer__user')[:10]
        
        # # 评价统计
        # reviews = ProductReview.objects.filter(product=product, is_approved=True)
        # context['review_stats'] = {
        #     'total': reviews.count(),
        #     'average': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
        #     'distribution': reviews.values('rating').annotate(count=Count('rating')).order_by('-rating')
        # }

        # 评价统计
        reviews_qs = ProductReview.objects.filter(product=product, is_approved=True)
        total_reviews = reviews_qs.count()
        average_rating = reviews_qs.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # 计算每个星级的分布和百分比
        distribution = reviews_qs.values('rating') \
            .annotate(count=Count('rating')) \
            .order_by('-rating')
        # 预计算百分比
        dist_list = []
        for item in distribution:
            percentage = (item['count'] / total_reviews * 100) if total_reviews > 0 else 0
            dist_list.append({
                'rating': item['rating'],
                'count': item['count'],
                'percentage': round(percentage, 1)  # 可保留一位小数
            })
        
        context['review_stats'] = {
            'total': total_reviews,
            'average': round(average_rating, 1),
            'distribution': dist_list
        }


        # 评价表单
        context['review_form'] = ProductReviewForm()
        
        # 获取属性值
        context['attributes'] = ProductAttributeValue.objects.filter(
            product=product
        ).select_related('attribute')
        
        return context
    
    def post(self, request, *args, **kwargs):
        """处理评价提交"""
        if not request.user.is_authenticated:
            messages.error(request, '请先登录后再评价')
            return redirect('accounts:login')
        
        product = self.get_object()
        customer = request.user.customer_profile if hasattr(request.user, 'customer_profile') else None
        
        if not customer:
            messages.error(request, '只有客户才能评价产品')
            return redirect('products:product_detail', slug=product.slug)
        
        form = ProductReviewForm(request.POST, product=product, customer=customer)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.customer = customer
            review.save()
            
            messages.success(request, '评价提交成功！审核通过后将显示')
            return redirect('products:product_detail', slug=product.slug)
        else:
            # 显示表单错误
            for error in form.errors.values():
                messages.error(request, error[0])
            
            context = self.get_context_data(**kwargs)
            context['review_form'] = form
            return render(request, self.template_name, context)


class CategoryDetailView(DetailView):
    """分类详情页"""
    model = ProductCategory
    template_name = 'products/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        
        # 获取该分类下的所有产品（包括子分类）
        products = category.get_all_products()
        
        # 分页
        paginator = Paginator(products, 20)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['products'] = page_obj
        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        
        # 获取子分类
        context['subcategories'] = category.children.filter(is_active=True)
        
        return context


def search_autocomplete(request):
    """搜索自动补全"""
    query = request.GET.get('q', '')
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(tags__icontains=query),
            is_active=True
        )[:10]
        
        results = [
            {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': str(product.price),
                'url': product.get_absolute_url(),
                'image': product.get_main_image().image.url if product.get_main_image() else ''
            }
            for product in products
        ]
    else:
        results = []
    
    return JsonResponse({'results': results})


# ============ 后台管理视图 ============

@method_decorator([login_required, staff_required], name='dispatch')
class ProductCreateView(CreateView):
    """创建产品"""
    model = Product
    form_class = ProductForm
    template_name = 'products/admin/product_form.html'
    success_url = reverse_lazy('products:admin_product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '创建产品'
        return context
    
    def form_valid(self, form):
        if hasattr(self.request.user, 'staff_profile'):
            form.instance.created_by = self.request.user
        
        product = form.save(commit=True)  # 先儲存產品

        # 處理附加圖片（多檔）
        additional_images = self.request.FILES.getlist('additional_images')
        for image in additional_images:
            ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=product.name
            )

        messages.success(self.request, '产品创建成功！')
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        messages.error(self.request, '请检查表单错误')
        return super().form_invalid(form)


@method_decorator([login_required, staff_required], name='dispatch')
class ProductUpdateView(UpdateView):
    """编辑产品"""
    model = Product
    form_class = ProductForm
    template_name = 'products/admin/product_form.html'
    success_url = reverse_lazy('products:admin_product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '编辑产品'
        context['images'] = self.object.images.all().order_by('display_order')
        return context
    
    def form_valid(self, form):
        product = form.save(commit=True)

        # 處理附加圖片（多檔）
        additional_images = self.request.FILES.getlist('additional_images')
        for image in additional_images:
            ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=product.name
            )

        messages.success(self.request, '产品更新成功！')
        return redirect(self.success_url)


@method_decorator([login_required, staff_required], name='dispatch')
class ProductDeleteView(DeleteView):
    """删除产品"""
    model = Product
    template_name = 'products/admin/product_confirm_delete.html'
    success_url = reverse_lazy('products:admin_product_list')
    
    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        product_name = product.name
        
        # 软删除：将产品标记为不活跃
        product.is_active = False
        product.save()
        
        messages.success(request, f'产品"{product_name}"已下架')
        return redirect(self.success_url)


@method_decorator([login_required, staff_required], name='dispatch')
class AdminProductListView(ListView):
    """后台产品列表"""
    model = Product
    template_name = 'products/admin/product_list.html'
    context_object_name = 'products'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Product.objects.all().order_by('-created_at')
        
        # 搜索功能
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 筛选功能
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'low_stock':
            queryset = queryset.filter(stock_quantity__lte=models.F('low_stock_threshold'))
        elif status == 'out_of_stock':
            queryset = queryset.filter(stock_quantity=0)
        
        return queryset.select_related('category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        
        # 统计信息
        context['total_products'] = Product.objects.count()
        context['active_products'] = Product.objects.filter(is_active=True).count()
        context['low_stock_products'] = Product.objects.filter(
            stock_quantity__lte=models.F('low_stock_threshold'),
            is_track_inventory=True
        ).count()
        
        return context


@method_decorator([login_required, admin_required], name='dispatch')
class CategoryListView(ListView):
    """分类列表"""
    model = ProductCategory
    template_name = 'products/admin/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return ProductCategory.objects.all().order_by('display_order', 'name')


@method_decorator([login_required, admin_required], name='dispatch')
class CategoryCreateView(CreateView):
    """创建分类"""
    model = ProductCategory
    form_class = ProductCategoryForm
    template_name = 'products/admin/category_form.html'
    success_url = reverse_lazy('products:admin_category_list')
    
    def form_valid(self, form):
        messages.success(self.request, '分类创建成功！')
        return super().form_valid(form)


@method_decorator([login_required, admin_required], name='dispatch')
class CategoryUpdateView(UpdateView):
    """编辑分类"""
    model = ProductCategory
    form_class = ProductCategoryForm
    template_name = 'products/admin/category_form.html'
    success_url = reverse_lazy('products:admin_category_list')
    
    def form_valid(self, form):
        messages.success(self.request, '分类更新成功！')
        return super().form_valid(form)


@method_decorator([login_required, admin_required], name='dispatch')
class CategoryDeleteView(DeleteView):
    """删除分类"""
    model = ProductCategory
    template_name = 'products/admin/category_confirm_delete.html'
    success_url = reverse_lazy('products:admin_category_list')
    
    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        
        # 检查是否有产品使用该分类
        if category.products.exists():
            messages.error(request, '该分类下有产品，无法删除')
            return redirect('products:admin_category_list')
        
        category.delete()
        messages.success(request, '分类删除成功！')
        return redirect(self.success_url)


@login_required
@staff_required
def toggle_product_status(request, pk):
    """切换产品状态"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.is_active = not product.is_active
        product.save()
        
        action = '上架' if product.is_active else '下架'
        messages.success(request, f'产品"{product.name}"已{action}')
    
    return redirect('products:admin_product_list')


@login_required
@staff_required
def update_product_images(request, pk):
    """更新产品图片"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # 处理主图片
        main_image = request.FILES.get('main_image')
        if main_image:
            ProductImage.objects.filter(product=product, is_main=True).delete()
            ProductImage.objects.create(
                product=product,
                image=main_image,
                is_main=True,
                alt_text=product.name
            )
        
        # 处理附加图片
        additional_images = request.FILES.getlist('additional_images')
        for image in additional_images:
            ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=product.name
            )
        
        messages.success(request, '图片更新成功！')
    
    return redirect('products:product_update', pk=pk)


@login_required
@staff_required
@require_POST
def delete_product_image(request, pk):
    """删除产品图片"""
    image = get_object_or_404(ProductImage, pk=pk)
    product_pk = image.product.pk
    
    # 检查是否是唯一的主图片
    if image.is_main and image.product.images.filter(is_main=True).count() == 1:
        return JsonResponse({
            'success': False,
            'message': '不能删除唯一的主图片'
        })
    
    image.delete()
    
    return JsonResponse({
        'success': True,
        'message': '图片删除成功'
    })


@login_required
@staff_required
@require_POST
def set_main_image(request, pk):
    """设置为主图片"""
    image = get_object_or_404(ProductImage, pk=pk)
    
    # 取消其他图片的主图状态
    ProductImage.objects.filter(product=image.product, is_main=True).update(is_main=False)
    
    # 设置当前图片为主图
    image.is_main = True
    image.save()
    
    return JsonResponse({
        'success': True,
        'message': '主图片设置成功'
    })


@login_required
@staff_required
def product_review_list(request):
    """产品评价列表"""
    reviews = ProductReview.objects.all().order_by('-created_at')
    
    # 筛选功能
    status = request.GET.get('status', '')
    if status == 'pending':
        reviews = reviews.filter(is_approved=False)
    elif status == 'approved':
        reviews = reviews.filter(is_approved=True)
    
    # 分页
    paginator = Paginator(reviews, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'products/admin/review_list.html', {
        'reviews': page_obj,
        'page_obj': page_obj,
        'status': status
    })


@login_required
@staff_required
@require_POST
def approve_review(request, pk):
    """审核评价"""
    review = get_object_or_404(ProductReview, pk=pk)
    review.is_approved = True
    review.save()
    
    messages.success(request, '评价已审核通过')
    return redirect('products:review_list')


@login_required
@staff_required
@require_POST
def delete_review(request, pk):
    """删除评价"""
    review = get_object_or_404(ProductReview, pk=pk)
    review.delete()
    
    messages.success(request, '评价已删除')
    return redirect('products:review_list')


def product_api(request, pk):
    """产品API接口"""
    product = get_object_or_404(Product, pk=pk)
    
    data = {
        'id': str(product.id),
        'sku': product.sku,
        'name': product.name,
        'price': str(product.price),
        'compare_at_price': str(product.compare_at_price) if product.compare_at_price else None,
        'discount_percentage': product.discount_percentage,
        'in_stock': product.in_stock,
        'stock_quantity': product.stock_quantity,
        'is_digital': product.is_digital,
        'availability': product.check_availability(),
        'main_image': product.get_main_image().image.url if product.get_main_image() else '',
        'url': product.get_absolute_url(),
    }
    
    return JsonResponse(data)
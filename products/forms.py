from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Product, ProductCategory, ProductImage, ProductReview


class ProductCategoryForm(forms.ModelForm):
    """产品分类表单"""
    class Meta:
        model = ProductCategory
        fields = [
            'name', 'slug', 'description', 'parent',
            'image', 'display_order', 'is_active',
            'meta_title', 'meta_description'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('name', ''))
        qs = ProductCategory.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('该URL标识已存在')
        return slug


class ProductForm(forms.ModelForm):
    """产品表单"""
    main_image = forms.ImageField(
        label='主图片',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'slug', 'category',
            'description', 'short_description',
            'price', 'cost_price', 'compare_at_price',
            'stock_quantity', 'reorder_level', 'low_stock_threshold',
            'is_track_inventory', 'allow_backorder',
            'weight', 'dimensions', 'color', 'size', 'material', 'brand',
            'is_active', 'is_featured', 'is_bestseller', 'is_new', 'is_digital',
            'meta_title', 'meta_description', 'meta_keywords',
            'tags'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'short_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'meta_keywords': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'compare_at_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        qs = Product.objects.filter(sku=sku)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('该SKU编码已存在')
        return sku

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('name', ''))
        qs = Product.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('该URL标识已存在')
        return slug

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError('价格必须大于0')
        return price

    def clean(self):
        cleaned_data = super().clean()
        compare_at_price = cleaned_data.get('compare_at_price')
        price = cleaned_data.get('price')
        if compare_at_price and price and compare_at_price <= price:
            raise ValidationError({'compare_at_price': '对比价格必须大于销售价格'})
        if cleaned_data.get('is_digital'):
            cleaned_data['is_track_inventory'] = False
            cleaned_data['allow_backorder'] = False
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=False)
        if commit:
            product.save()
            # 處理主圖
            if self.cleaned_data.get('main_image'):
                ProductImage.objects.filter(product=product, is_main=True).delete()
                ProductImage.objects.create(
                    product=product,
                    image=self.cleaned_data['main_image'],
                    is_main=True,
                    alt_text=product.name
                )
        return product


# 其餘表單（ProductImageForm、ProductSearchForm、ProductReviewForm）保持不變，可直接保留原本正確版本
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_main', 'display_order']
        widgets = {
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductSearchForm(forms.Form):
    q = forms.CharField(label='搜索关键词', required=False,
                        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '搜索产品...'}))
    category = forms.ModelChoiceField(label='产品分类', queryset=ProductCategory.objects.filter(is_active=True),
                                      required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    min_price = forms.DecimalField(label='最低价格', required=False,
                                   widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    max_price = forms.DecimalField(label='最高价格', required=False,
                                   widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    sort_by = forms.ChoiceField(label='排序方式', required=False, choices=[
        ('newest', '最新'), ('price_asc', '价格从低到高'), ('price_desc', '价格从高到低'),
        ('name_asc', '名称A-Z'), ('name_desc', '名称Z-A'), ('rating', '评分最高'), ('popular', '最受欢迎')
    ], widget=forms.Select(attrs={'class': 'form-control'}))
    in_stock = forms.BooleanField(label='仅显示有货', required=False,
                                  widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    is_featured = forms.BooleanField(label='推荐产品', required=False,
                                     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    is_new = forms.BooleanField(label='新品', required=False,
                                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.product and self.customer:
            if ProductReview.objects.filter(product=self.product, customer=self.customer).exists():
                raise ValidationError('您已经评价过此产品')
        return cleaned_data
from django import forms

MAX_IMAGE_FILES = 30
MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_ZIP_SIZE = 25 * 1024 * 1024


def _validate_upload_batch(images, zip_file):
    if len(images) > MAX_IMAGE_FILES:
        raise forms.ValidationError(f"الحد الأعلى {MAX_IMAGE_FILES} صورة في العملية الواحدة.")
    oversized = [item.name for item in images if getattr(item, "size", 0) > MAX_IMAGE_SIZE]
    if oversized:
        raise forms.ValidationError("حجم كل صورة يجب ألا يتجاوز 8 ميجابايت.")
    if zip_file and getattr(zip_file, "size", 0) > MAX_ZIP_SIZE:
        raise forms.ValidationError("حجم ملف ZIP يجب ألا يتجاوز 25 ميجابايت.")


from .models import BlogCategory, BlogComment, City, Page, Service


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return single_file_clean(data, initial)


class AIContentGeneratorForm(forms.Form):
    CONTENT_TYPE_CHOICES = [
        ("blog_post", "مقال"),
        ("service", "خدمة"),
        ("city", "تحديث مدينة ثابتة"),
        ("page", "صفحة"),
        ("city_service", "خدمة داخل مدينة"),
        ("bulk", "أمر شامل: مدن وخدمات وصفحات ومقالات"),
    ]
    MODE_CHOICES = [
        ("create", "إنشاء جديد"),
        ("update", "تحديث محتوى موجود"),
        ("bulk", "تنفيذ أمر شامل"),
    ]

    content_type = forms.ChoiceField(choices=CONTENT_TYPE_CHOICES, label="نوع المحتوى")
    mode = forms.ChoiceField(choices=MODE_CHOICES, initial="create", label="طريقة التنفيذ")
    object_id = forms.IntegerField(required=False, min_value=1, label="رقم العنصر للتحديث")
    title_hint = forms.CharField(required=False, label="عنوان أو فكرة أولية")
    prompt = forms.CharField(
        label="طلبك للذكاء الاصطناعي",
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": (
                    "مثال: حدّث وصف مدينة الرياض، أو أنشئ مقالة عن زراعة النخيل وحدد المدينة المناسبة "
                    "مع تحسين العناوين والوصف لمحركات البحث."
                ),
            }
        ),
    )
    images = MultipleFileField(required=False, widget=MultipleFileInput(attrs={"multiple": True}), label="صور مرجعية")
    publish_now = forms.BooleanField(required=False, initial=False, label="نشر المحتوى مباشرة إذا كان النوع يدعم النشر")
    create_page_media = forms.BooleanField(required=False, initial=True, label="إنشاء وسائط للصفحة من الصور المرفوعة عند الإمكان")
    blog_category = forms.ModelChoiceField(queryset=BlogCategory.objects.none(), required=False, label="تصنيف المقال")
    blog_tags = forms.CharField(required=False, label="وسوم المقال", help_text="افصل الوسوم بفاصلة")
    city = forms.ModelChoiceField(queryset=City.objects.none(), required=False, label="المدينة المرتبطة")
    service = forms.ModelChoiceField(queryset=Service.objects.none(), required=False, label="الخدمة المرتبطة")
    page_template_key = forms.ChoiceField(
        required=False,
        choices=[("", "اختر القالب")] + list(Page.TEMPLATE_CHOICES),
        label="قالب الصفحة",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["blog_category"].queryset = BlogCategory.objects.order_by("name")
        self.fields["city"].queryset = City.objects.filter(is_active=True, is_system=True).order_by("name")
        self.fields["service"].queryset = Service.objects.order_by("title")

    def clean(self):
        cleaned = super().clean()
        images = self.files.getlist("images") if self.files else []
        _validate_upload_batch(images, None)
        content_type = cleaned.get("content_type")
        mode = cleaned.get("mode")
        if content_type == "bulk":
            cleaned["mode"] = "bulk"
        elif content_type == "city":
            if mode != "update":
                self.add_error("mode", "المدن ثابتة؛ اختر تحديث محتوى موجود بدل إنشاء مدينة جديدة.")
            if not cleaned.get("city") and not cleaned.get("object_id"):
                self.add_error("city", "اختر المدينة الثابتة التي تريد تحديث محتواها.")
        return cleaned


class LibraryImageBulkUploadForm(forms.Form):
    DISTRIBUTION_CHOICES = [
        ("all", "توزيع تلقائي على كل أماكن الموقع"),
        ("single", "إضافة كل الصور إلى مكان واحد"),
    ]

    distribution_mode = forms.ChoiceField(
        choices=DISTRIBUTION_CHOICES,
        initial="all",
        label="طريقة التوزيع",
    )
    usage_group = forms.ChoiceField(
        required=False,
        choices=[],
        label="المكان عند اختيار مكان واحد",
    )
    category = forms.ChoiceField(
        required=False,
        choices=[],
        label="تصنيف الصور",
    )
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "image/*"}),
        label="رفع صور جديدة",
    )
    zip_file = forms.FileField(required=False, label="أو ارفع ملف ZIP يحتوي الصور")
    activate_now = forms.BooleanField(required=False, initial=True, label="تفعيل الصور مباشرة في الموقع")

    def __init__(self, *args, **kwargs):
        from .models import LibraryImage

        super().__init__(*args, **kwargs)
        self.fields["usage_group"].choices = [("", "توزيع تلقائي")] + list(LibraryImage.USAGE_GROUP_CHOICES)
        self.fields["category"].choices = [("", "عام / تلقائي")] + list(LibraryImage.CATEGORY_CHOICES)

    def clean(self):
        cleaned = super().clean()
        images = self.files.getlist("images") if self.files else []
        zip_file = self.files.get("zip_file") if self.files else None
        if not images and not zip_file:
            raise forms.ValidationError("ارفع صورًا متعددة أو ملف ZIP يحتوي الصور.")
        if zip_file and not zip_file.name.lower().endswith(".zip"):
            raise forms.ValidationError("ملف ZIP يجب أن ينتهي بالامتداد .zip.")
        _validate_upload_batch(images, zip_file)
        if cleaned.get("distribution_mode") == "single" and not cleaned.get("usage_group"):
            raise forms.ValidationError("اختر مكانًا واحدًا عند استخدام وضع الإضافة إلى مكان واحد.")
        return cleaned


class LibraryImageBulkReplaceForm(forms.Form):
    SCOPE_CHOICES = [
        ("active", "الصور المفعلة فقط"),
        ("all", "كل صور المكتبة"),
    ]
    MATCH_MODE_CHOICES = [
        ("order", "حسب ترتيب الصور في لوحة التحكم"),
        ("source_name", "حسب اسم الملف الأصلي"),
    ]

    scope = forms.ChoiceField(choices=SCOPE_CHOICES, initial="active", label="نطاق الاستبدال")
    match_mode = forms.ChoiceField(choices=MATCH_MODE_CHOICES, initial="order", label="طريقة مطابقة الصور")
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "image/*"}),
        label="رفع صور متعددة",
    )
    zip_file = forms.FileField(required=False, label="أو ارفع ملف ZIP يحتوي الصور")
    clear_external_url = forms.BooleanField(
        required=False,
        initial=True,
        label="تعطيل الرابط الخارجي بعد رفع الصورة الجديدة",
        help_text="اتركها مفعلة حتى تظهر الصورة المرفوعة بدل أي رابط خارجي قديم.",
    )

    def clean(self):
        cleaned = super().clean()
        images = self.files.getlist("images") if self.files else []
        zip_file = self.files.get("zip_file") if self.files else None
        if not images and not zip_file:
            raise forms.ValidationError("ارفع صورًا متعددة أو ملف ZIP يحتوي الصور.")
        if zip_file and not zip_file.name.lower().endswith(".zip"):
            raise forms.ValidationError("ملف ZIP يجب أن ينتهي بالامتداد .zip.")
        _validate_upload_batch(images, zip_file)
        return cleaned


class BlogCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ["author_name", "author_email", "content"]
        widgets = {
            "author_name": forms.TextInput(attrs={"placeholder": "الاسم"}),
            "author_email": forms.EmailInput(attrs={"placeholder": "البريد الإلكتروني"}),
            "content": forms.Textarea(attrs={"rows": 5, "placeholder": "اكتب تعليقك هنا"}),
        }

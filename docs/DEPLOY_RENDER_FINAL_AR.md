# نشر نخيل نجد V6 على Render

المشروع مجهز كـRender Blueprint واحد. ملف `render.yaml` ينشئ قاعدة PostgreSQL وخدمة Django وخدمة Next.js، ثم يربط الواجهة بالباك إند عبر شبكة Render الخاصة.

## قبل الرفع

1. فك ضغط المشروع وارفع **محتويات المجلد نفسه** إلى مستودع Git، بحيث يكون `render.yaml` في الجذر.
2. جهز حساب Cloudinary وخذ قيمة بالشكل `cloudinary://API_KEY:API_SECRET@CLOUD_NAME`.
3. جهز كلمة عشوائية طويلة للربط بين Next.js وDjango. استخدم القيمة نفسها في متغير `FRONTEND_API_SECRET` عند الخدمتين.

## إنشاء الـBlueprint

1. من Render اختر **New → Blueprint**.
2. اربط المستودع واضغط Apply.
3. عند طلب القيم السرية أدخل:

| الخدمة | المتغير | المطلوب |
|---|---|---|
| Django | `CLOUDINARY_URL` | رابط Cloudinary الكامل |
| Django | `FRONTEND_API_SECRET` | كلمة عشوائية طويلة |
| Next.js | `FRONTEND_API_SECRET` | **نفس** كلمة Django بالضبط |
| Django | `DJANGO_SUPERUSER_USERNAME` | اسم مدير لوحة التحكم |
| Django | `DJANGO_SUPERUSER_PASSWORD` | كلمة مرور قوية للمدير |

Render ينشئ `DJANGO_SECRET_KEY` و`DATABASE_URL` تلقائيًا، ويحقن عنوان ومنفذ Django الخاصين في خدمة Next.js.

## ما يحدث تلقائيًا

- تثبيت متطلبات Python وNode.
- فحص الـCSS والمحتوى وملف Blueprint.
- التأكد من عدم وجود migrations ناقصة.
- بناء ملفات Django الثابتة وبناء Next.js الإنتاجي.
- تشغيل migrations وإنشاء المدير ومزامنة الكتالوج الآمن.
- تشغيل Gunicorn على منفذ Render وتشغيل Next.js على `0.0.0.0`.

## فحص النشر

بعد اكتمال الخدمتين افتح:

- `https://nakheel-najd.onrender.com/api/v1/ready/`
- `https://getsiaq-frontend.onrender.com/api/health/`

النتيجة الصحيحة تحتوي `"ok": true` و`"database": "ready"` أو `"backend": "ready"`.

من Render Shell للباك إند شغّل مرة واحدة:

```bash
python manage.py check_cloudinary_storage
python manage.py ensure_public_catalog
```

## ربط النطاق

النطاق المجهز داخل المشروع هو `getsiaq.online`. اربطه بخدمة `getsiaq-frontend` من Custom Domains، ثم حدّث DNS حسب القيم التي يعرضها Render. لا تربط النطاق العام بخدمة Django؛ Django يبقى API ولوحة إدارة.

## ملاحظة الخطة

الـBlueprint يستخدم خطة Render المجانية لتسهيل التجربة الأولى. للإطلاق التجاري الفعلي يوصى بترقية خدمتي الويب وقاعدة PostgreSQL لتجنب النوم وحدود الخطة المجانية.

# دليل رفع نخيل نجد V6.4 على Render

المشروع جاهز كـRender Blueprint؛ ملف `render.yaml` ينشئ PostgreSQL وخدمة Django وخدمة Next.js ويربطهما داخليًا.

## 1. رفع المشروع إلى GitHub

بعد فك الملف، تأكد أن `manage.py` و`render.yaml` و`frontend/` موجودة مباشرة في جذر المجلد، ثم نفذ من داخله:

```bash
git init
git branch -M main
git add .
git commit -m "Release V6.4 design and media control"
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

إذا كان `origin` موجودًا، افحصه أولًا بـ`git remote -v` ثم استخدم `git remote set-url origin ...`. لا تستخدم `--force` إلا إذا كنت متأكدًا أنك تريد استبدال تاريخ الفرع.

## 2. إنشاء Blueprint في Render

1. افتح Render ثم **New > Blueprint**.
2. اربط مستودع GitHub واختر الفرع `main`.
3. Render سيقرأ `render.yaml` وينشئ:
   - `nakheel-najd-db`
   - `nakheel-najd` للباك إند
   - `getsiaq-frontend` للواجهة
4. أدخل القيم السرية التي يطلبها Blueprint ثم اضغط Apply.

## 3. القيم السرية المطلوبة

في خدمة Django `nakheel-najd`:

```text
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
FRONTEND_API_SECRET=<قيمة عشوائية طويلة>
DJANGO_SUPERUSER_USERNAME=<اسم مدير جديد>
DJANGO_SUPERUSER_PASSWORD=<كلمة مرور قوية>
```

وفي خدمة Next.js `getsiaq-frontend`:

```text
FRONTEND_API_SECRET=<نفس القيمة الموجودة في خدمة Django حرفيًا>
```

لا تضع الأسرار في GitHub أو داخل ملفات المشروع. الربط الداخلي `DJANGO_API_HOST` و`DJANGO_API_PORT` وقاعدة البيانات تُضبط تلقائيًا من Blueprint.

## 4. النطاق

اربط `getsiaq.online` و`www.getsiaq.online` بخدمة `getsiaq-frontend` فقط. خدمة Django تبقى خلف الواجهة، واسم Render الخارجي الخاص بها يُضاف تلقائيًا إلى `ALLOWED_HOSTS`.

## 5. التحقق بعد النشر

من Shell خدمة Django نفذ:

```bash
python manage.py check_cloudinary_storage
python manage.py ensure_public_catalog
```

ثم افتح:

```text
https://getsiaq.online/api/health/
https://getsiaq.online/
https://getsiaq.online/services/
https://getsiaq.online/admin/
```

النتيجة المتوقعة لفحص الكتالوج:

```text
cities=12/12, services=250/250, portfolio=93/93, local=96/96, local_pages=600/600
```

إذا ظهر من Cloudinary خطأ يحتوي `actions=["create"]` فالمفتاح لا يملك صلاحية إنشاء Asset؛ عدّل صلاحية المفتاح في Cloudinary ثم أعد الفحص.

## 6. إعادة الرفع لاحقًا

بعد أي تعديل محلي:

```bash
git add .
git commit -m "Describe the update"
git push origin main
```

خدمات Render مضبوطة على النشر التلقائي عند كل Commit. في الخطة المجانية قد تتأخر أول زيارة بعد السكون بسبب Cold Start.

# دليل النشر النهائي — نخيل نجد V5.0

## 1. ارفع المشروع من مجلد Git نظيف

سبب مهم: لا تستخدم Git الموجود في `C:\Users\user` أو أي مستودع أب. المشروع يجب أن يملك `.git` داخل مجلده نفسه.

بعد فك الملف النهائي في:

```text
C:\Users\user\Downloads\cxa-landscape-v5.0-final
```

تأكد أن الملفات التالية موجودة مباشرة داخل هذا المجلد:

```text
manage.py
render.yaml
requirements.txt
core\
project\
frontend\
```

ثم افتح PowerShell داخل المجلد ونفذ:

```powershell
git init .
git branch -M main
git remote add origin https://github.com/vfvgfdvgf/cxa-landscape.git
git fetch origin main
git rev-parse --show-toplevel
git remote -v
```

يجب أن يكون `git rev-parse --show-toplevel` بالضبط:

```text
C:/Users/user/Downloads/cxa-landscape-v5.0-final
```

ويجب أن يكون `origin` هو:

```text
https://github.com/vfvgfdvgf/cxa-landscape.git
```

إذا تحقق الشرطان:

```powershell
git add .
git commit -m "V5 final production release"
git push -u origin main --force
```

استخدام `--force` هنا مقصود لتنظيف تاريخ الفرع من الرفع السابق الذي احتوى مسارات `Downloads/...`. لا تستخدمه قبل التأكد من اسم المستودع وGit root أعلاه.

## 2. متغيرات Backend في Render

المتغيرات الحساسة لا توضع في GitHub. استخدم Render Environment:

```text
DATABASE_URL=<Render PostgreSQL URL>
USE_CLOUDINARY_MEDIA=True
CLOUDINARY_CLOUD_NAME=<cloud name>
CLOUDINARY_API_KEY=<api key>
CLOUDINARY_API_SECRET=<api secret>
FRONTEND_API_SECRET=<random long shared secret>
DJANGO_SUPERUSER_USERNAME=<admin username>
DJANGO_SUPERUSER_PASSWORD=<strong one-time password>
```

اختياري:

```text
TOKENMIX_API_KEY=<only if AI SEO is used>
GOOGLE_SERVICE_ACCOUNT_JSON=<only if Search Console data import is used>
```

لا تستخدم `CLOUDINARY_URL` في هذه النسخة؛ الإعداد القياسي للإنتاج هو المتغيرات الثلاثة المنفصلة.

## 3. متغيرات Frontend في Render

```text
NEXT_PUBLIC_SITE_URL=https://getsiaq.online
DJANGO_API_URL=https://nakheel-najd.onrender.com
DJANGO_API_SECRET=<exact same value as FRONTEND_API_SECRET>
```

`render.yaml` يثبت Node 22 LTS.

## 4. ما يفعله Deploy تلقائيًا

Backend build:

```text
install requirements
build_public_assets
static_audit
makemigrations --check --dry-run
manage.py check
collectstatic
```

Backend startup:

1. يطبق migrations.
2. يتأكد من مستخدم الإدارة.
3. يبدأ فحص/إصلاح الكتالوج في الخلفية.
4. يفتح Gunicorn المنفذ مباشرة دون انتظار مزامنة 250 خدمة والمشاريع.

Frontend build:

```text
npm ci --include=dev  # frontend/.npmrc يحتوي include=dev أيضًا كحماية إضافية
npm run typecheck   # يشغّل next typegen ثم tsc --noEmit
npm run build
```

## 5. التحقق بعد أن يصبح Backend Live

من Render Shell:

```bash
python manage.py check_cloudinary_storage
python manage.py ensure_public_catalog
```

ويجب أن ينتهي فحص الكتالوج إلى:

```text
cities=12/12, services=250/250, portfolio=93/93, local=96/96, local_pages=600/600
```

ثم افتح:

```text
https://nakheel-najd.onrender.com/health/
https://getsiaq.online/api/health/
https://getsiaq.online/services/
https://getsiaq.online/projects/
```

## 6. Cloudinary

إذا ظهر:

```text
Request forbidden due to missing permissions (actions=["create"])
```

فالكود وصل إلى Cloudinary بنجاح، لكن المفتاح لا يملك صلاحية إنشاء Asset. عدّل Role للمفتاح أو استخدم مفتاحًا يملك upload/create، ثم أعد:

```bash
python manage.py check_cloudinary_storage
```

لا ترسل `CLOUDINARY_API_SECRET` في المحادثات أو GitHub.

## 7. إثبات Google Search Console

من Django Admin > إعدادات الموقع/إثبات ملكية الموقع يمكنك إدخال:

- HTML tag: يضاف إلى `<head>` تلقائيًا.
- HTML file: يقدم من جذر `getsiaq.online/google....html`.
- DNS TXT أو CNAME: تحفظ القيم في اللوحة لتنسخها إلى مزود DNS.
- Google Analytics.
- Google Tag Manager.

لـDomain Property مثل `sc-domain:getsiaq.online` يجب تنفيذ سجل DNS لدى مزود الدومين؛ التطبيق لا يستطيع تعديل DNS بنفسه.

## 8. ملاحظة Render Free

تحسينات الكود تقلل حجم الصور وطلبات API وزمن الانتقال، لكن Free instance قد يدخل في sleep، لذلك أول زيارة بعد السكون قد تتأخر بسبب Cold Start. هذا عامل استضافة وليس مشكلة في تحميل الصور نفسها.

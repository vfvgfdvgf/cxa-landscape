# إصلاح فشل Render — JSX / TypeScript

## سبب المشكلة

خدمة الواجهة تضبط `NODE_ENV=production` أثناء البناء. npm عندها قد يستبعد `devDependencies` افتراضيًا، بينما `typescript` و`@types/react` و`@types/react-dom` موجودة ضمن `devDependencies`. النتيجة أن TypeScript لا يجد تعريفات JSX ويظهر الخطأ `JSX.IntrinsicElements`.

## الإصلاح المطبق

- إضافة `frontend/.npmrc` بالقيمة `include=dev` حتى يثبت `npm ci` حزم البناء حتى مع `NODE_ENV=production`.
- تعديل Build Command في `render.yaml` إلى `npm ci --include=dev && npm run typecheck && npm run build`.
- تعديل `npm run typecheck` إلى `next typegen && tsc --noEmit` حتى تتولد أنواع Next.js قبل تشغيل TypeScript.
- تحديث التدقيق الساكن ليتأكد من بقاء هذا الإصلاح في الإصدارات القادمة.

## ملاحظة للخدمة الموجودة مسبقًا

حتى لو بقي Build Command القديم في لوحة Render (`npm ci && npm run typecheck && npm run build`) فملف `.npmrc` يجعل `npm ci` يثبت devDependencies، لذلك لا يعتمد الإصلاح على تحديث Blueprint وحده.

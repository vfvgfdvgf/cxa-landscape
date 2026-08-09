# نشر V6.4 النهائي

الدليل المعتمد للإنتاج موجود في جذر المشروع: `DEPLOYMENT_AR.md`.

نقاط إلزامية:
- Git root يجب أن يكون مجلد المشروع نفسه لا `C:/Users/user`.
- Backend يستخدم PostgreSQL + `CLOUDINARY_URL` حسب `render.yaml`.
- Frontend يستخدم Node 22 LTS.
- قيمة `DJANGO_API_SECRET` في Frontend تطابق `FRONTEND_API_SECRET` في Backend.
- بعد Live شغّل `python manage.py check_cloudinary_storage` و`python manage.py ensure_public_catalog`.

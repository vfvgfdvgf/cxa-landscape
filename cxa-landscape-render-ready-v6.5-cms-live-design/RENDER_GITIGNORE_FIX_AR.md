# إصلاح Render V6.2 — CinematicVideo

سبب الفشل كان قاعدة `media/` العامة داخل `.gitignore`.
هذه القاعدة تجعل Git يتجاهل أي مجلد باسم `media` في أي مستوى، بما في ذلك:

`frontend/components/media/CinematicVideo.tsx`

تم تعديل القاعدة إلى `/media/` بحيث تتجاهل مجلد وسائط Django في جذر المشروع فقط، ولا تتجاهل مكونات الواجهة.
كما أضيف فحص إلى `scripts/static_audit.py` لمنع رجوع المشكلة.

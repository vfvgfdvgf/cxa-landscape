# GitHub + Render — الطريقة الآمنة لهذه النسخة

استخدم دائمًا مجلدًا جديدًا مستقلًا للمشروع. لا تنفذ `git add .` إذا كان `git rev-parse --show-toplevel` يعرض `C:/Users/user`.

المستودع المقصود:

```text
https://github.com/vfvgfdvgf/cxa-landscape.git
```

الرفع النهائي الموصى به موضح بالكامل في `DEPLOYMENT_AR.md`. قبل أي Push تأكد من شرطين:

```powershell
git rev-parse --show-toplevel
git remote -v
```

Git root يجب أن يكون مجلد V5 النهائي نفسه، و`origin` يجب أن يكون مستودع `cxa-landscape` فقط.

لا تنفذ `git pull` لدمج تاريخ المشروع القديم الملوث بمسارات `Downloads/...`. في الإصدار النهائي يتم إنشاء root نظيف ثم استبدال `main` مرة واحدة بعد التحقق باستخدام `--force`.

بعد Push، Render Blueprint يبني Backend وFrontend من `render.yaml`. لا تغيّر Root Directory للBackend؛ Frontend وحده يستخدم `frontend`.

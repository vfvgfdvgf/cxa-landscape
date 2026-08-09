"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="ar" dir="rtl">
      <body><main className="error-page"><h1>تعذر تشغيل الموقع مؤقتًا</h1><p>يرجى إعادة المحاولة، أو التواصل معنا إذا استمرت المشكلة.</p><button type="button" className="button" onClick={() => reset()}>إعادة المحاولة</button></main></body>
    </html>
  );
}

"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <section className="error-page">
      <p className="eyebrow">تعذر تحميل الصفحة</p>
      <h1>حدث انقطاع مؤقت</h1>
      <p>تعذر إكمال الطلب الآن. أعد المحاولة بعد لحظات، وستبقى في الصفحة نفسها.</p>
      <button className="button" type="button" onClick={() => reset()}>إعادة المحاولة</button>
    </section>
  );
}

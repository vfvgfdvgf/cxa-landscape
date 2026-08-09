import Link from "next/link";

export default function NotFound() {
  return (
    <section className="error-page">
      <p className="eyebrow">404 · مسار غير متاح</p>
      <h1>لنوصلك إلى المكان الصحيح</h1>
      <p>قد يكون الرابط قديمًا أو غير مكتمل. يمكنك العودة للرئيسية أو البحث عن الحي من الدليل.</p>
      <div className="button-row">
        <Link className="button" href="/districts/">دليل الأحياء</Link>
        <Link className="button button--ghost" href="/">العودة للرئيسية</Link>
      </div>
    </section>
  );
}

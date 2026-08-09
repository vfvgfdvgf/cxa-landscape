export default function Loading() {
  return (
    <section className="route-loading" role="status" aria-live="polite">
      <div className="route-loading__mark" aria-hidden="true">ن</div>
      <div className="route-loading__copy">
        <span>نخيل نجد</span>
        <strong>نجهّز تفاصيل الصفحة</strong>
      </div>
      <div className="route-loading__bar" aria-hidden="true"><span /></div>
      <span className="sr-only">جارٍ تحميل الصفحة</span>
    </section>
  );
}

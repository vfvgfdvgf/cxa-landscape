import Link from "next/link";

import { Container } from "@/components/ui/Container";

export function CallToAction({ title = "لنبنِ مساحة خارجية تناسب موقعك", description = "أرسل تفاصيل الموقع والخدمة المطلوبة، وسيتواصل معك الفريق لترتيب المعاينة." }: { title?: string; description?: string }) {
  return (
    <section className="content-section content-section--tinted">
      <Container>
        <div className="calculator">
          <div><p className="eyebrow">الخطوة التالية</p><h2>{title}</h2><p>{description}</p></div>
          <div className="calculator__result"><strong>معاينة</strong><span>لفهم الاحتياج قبل التسعير</span><Link className="button" href="/contact/">أرسل طلبك</Link></div>
        </div>
      </Container>
    </section>
  );
}

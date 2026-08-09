"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";

import type { SubmissionResponse } from "@/types";

export function LeadForm({ endpoint = "contact", services = [], cities = [], defaultService = "", defaultCity = "" }: { endpoint?: "contact" | "quote-request"; services?: string[]; cities?: string[]; defaultService?: string; defaultCity?: string }) {
  const [state, setState] = useState<{ loading: boolean; message: string; ok: boolean | null }>({ loading: false, message: "", ok: null });
  const submittingRef = useRef(false);
  const quoteRequest = endpoint === "quote-request";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    if (submittingRef.current) return;
    submittingRef.current = true;
    const values = Object.fromEntries(new FormData(form).entries());
    setState({ loading: true, message: "", ok: null });
    try {
      const response = await fetch(`/api/${endpoint}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...values, privacy_consent: values.privacy_consent === "on", page_url: window.location.href }),
      });
      const data = (await response.json()) as SubmissionResponse & { detail?: string; errors?: Record<string, string[]> };
      if (!response.ok) throw new Error(data.detail || "تحقق من الحقول ثم أعد المحاولة.");
      setState({ loading: false, message: data.message, ok: true });
      form.reset();
    } catch (error) {
      setState({ loading: false, message: error instanceof Error ? error.message : "تعذر إرسال الطلب.", ok: false });
    } finally {
      submittingRef.current = false;
    }
  }

  return (
    <form className="lead-form" onSubmit={submit} noValidate>
      <div className="form-field"><label htmlFor="lead-name">الاسم الكامل</label><input id="lead-name" name="name" minLength={2} maxLength={120} autoComplete="name" required /></div>
      <div className="form-field"><label htmlFor="lead-phone">رقم الجوال</label><input id="lead-phone" name="phone" type="tel" inputMode="tel" minLength={8} maxLength={20} autoComplete="tel" required /></div>
      <div className="form-field"><label htmlFor="lead-email">البريد الإلكتروني <span>(اختياري)</span></label><input id="lead-email" name="email" type="email" autoComplete="email" /></div>
      <div className="form-field"><label htmlFor="lead-city">المدينة</label>{cities.length ? <select id="lead-city" name="city" defaultValue={defaultCity}><option value="">اختر المدينة</option>{cities.map((city) => <option key={city} value={city}>{city}</option>)}</select> : <input id="lead-city" name="city" maxLength={120} autoComplete="address-level2" defaultValue={defaultCity} />}</div>
      <div className="form-field"><label htmlFor="lead-district">الحي <span>(اختياري)</span></label><input id="lead-district" name="district" maxLength={140} /></div>
      <div className="form-field"><label htmlFor="lead-service">الخدمة</label>{services.length ? <select id="lead-service" name="service" defaultValue={defaultService}><option value="">اختر الخدمة</option>{services.map((service) => <option key={service} value={service}>{service}</option>)}</select> : <input id="lead-service" name="service" maxLength={180} defaultValue={defaultService} />}</div>
      {quoteRequest ? <>
        <div className="form-field"><label htmlFor="lead-area">مساحة المشروع <span>(اختياري)</span></label><input id="lead-area" name="project_area" maxLength={80} placeholder="مثال: 350 متر مربع" /></div>
        <div className="form-field"><label htmlFor="lead-budget">الميزانية التقريبية <span>(اختياري)</span></label><select id="lead-budget" name="budget" defaultValue=""><option value="">اختر نطاقًا تقريبيًا</option><option>أقل من 25,000 ريال</option><option>25,000 - 50,000 ريال</option><option>50,000 - 80,000 ريال</option><option>80,000 - 150,000 ريال</option><option>أكثر من 150,000 ريال</option><option>أحتاج مساعدة في التقدير</option></select></div>
        <div className="form-field form-field--full"><label htmlFor="lead-contact-time">الوقت المفضل للتواصل <span>(اختياري)</span></label><select id="lead-contact-time" name="preferred_contact_time" defaultValue=""><option value="">اختر الوقت المناسب</option><option>صباحًا (8 - 12)</option><option>ظهرًا (12 - 4)</option><option>مساءً (4 - 8)</option><option>أي وقت</option></select></div>
      </> : null}
      <div className="form-field form-field--full"><label htmlFor="lead-message">تفاصيل الطلب</label><textarea id="lead-message" name="message" minLength={5} maxLength={3000} required /></div>
      <div className="form-field" aria-hidden="true" style={{ position: "absolute", insetInlineStart: "-9999px" }}><label htmlFor="lead-company">الشركة</label><input id="lead-company" name="company" tabIndex={-1} autoComplete="off" /></div>
      <label className="form-consent"><input name="privacy_consent" type="checkbox" required /><span>أوافق على استخدام بياناتي للتواصل بشأن هذا الطلب وفق <Link href="/privacy/">سياسة الخصوصية</Link>.</span></label>
      {state.message ? <p className={`form-status form-status--${state.ok ? "success" : "error"}`} role="status" aria-live="polite">{state.message}</p> : null}
      <div className="form-field--full"><button className="button" type="submit" disabled={state.loading}>{state.loading ? "جارٍ الإرسال…" : endpoint === "quote-request" ? "اطلب عرض السعر" : "إرسال الطلب"}</button></div>
    </form>
  );
}

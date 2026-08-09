from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse

from .ai_content import AIContentError, is_tokenmix_configured, request_tokenmix_generation, save_generated_content
from .forms import AIContentGeneratorForm
from .models import AIContentGenerationLog


def ai_content_admin_view(request, admin_site):
    form = AIContentGeneratorForm(request.POST or None, request.FILES or None)
    generated_payload = None
    saved_object = None
    saved_object_admin_url = ""
    log_entry = None
    ai_key_configured = is_tokenmix_configured()

    if request.method == "POST" and form.is_valid():
        if not ai_key_configured:
            messages.error(
                request,
                "تعذر تشغيل مولد المحتوى: أضف TOKENMIX_API_KEY في متغيرات البيئة ثم أعد تشغيل السيرفر.",
            )
        else:
            uploaded_files = request.FILES.getlist("images")
            log_entry = AIContentGenerationLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                content_type=form.cleaned_data["content_type"],
                mode=form.cleaned_data["mode"],
                prompt=form.cleaned_data["prompt"],
                title_hint=form.cleaned_data.get("title_hint", ""),
                image_count=len(uploaded_files),
                input_payload={
                    "content_type": form.cleaned_data["content_type"],
                    "mode": form.cleaned_data["mode"],
                    "object_id": form.cleaned_data.get("object_id"),
                    "publish_now": form.cleaned_data.get("publish_now"),
                },
            )
            try:
                generated_payload, request_meta, raw_response = request_tokenmix_generation(form, uploaded_files)
                saved_object = save_generated_content(form, generated_payload, uploaded_files)
                if hasattr(saved_object, "_meta"):
                    saved_object_admin_url = reverse(
                        f"admin:{saved_object._meta.app_label}_{saved_object._meta.model_name}_change",
                        args=[saved_object.pk],
                    )
                log_entry.status = "completed"
                log_entry.generated_payload = {
                    "request_meta": request_meta,
                    "raw_response_id": raw_response.get("id"),
                    "generated_payload": generated_payload,
                }
                if hasattr(saved_object, "_meta"):
                    log_entry.target_object_type = saved_object._meta.label
                    log_entry.target_object_id = saved_object.pk
                else:
                    log_entry.target_object_type = "bulk"
                    log_entry.generated_payload["bulk_counts"] = saved_object
                log_entry.save(update_fields=["status", "generated_payload", "target_object_type", "target_object_id", "updated_at"])
                messages.success(request, "تم إنشاء أو تحديث المحتوى بالذكاء الاصطناعي وحفظه في لوحة التحكم.")
            except AIContentError as exc:
                log_entry.status = "failed"
                log_entry.error_message = str(exc)
                log_entry.generated_payload = {
                    "raw_response_id": exc.raw_response.get("id") if exc.raw_response else "",
                    "raw_text_excerpt": (exc.raw_text or "")[:4000],
                }
                log_entry.save(update_fields=["status", "error_message", "generated_payload", "updated_at"])
                messages.error(request, f"تعذر إكمال العملية: {exc}")
            except Exception as exc:
                log_entry.status = "failed"
                log_entry.error_message = str(exc)
                log_entry.save(update_fields=["status", "error_message", "updated_at"])
                messages.error(request, f"تعذر إكمال العملية: {exc}")

    context = {
        **admin_site.each_context(request),
        "title": "مولد المحتوى بالذكاء الاصطناعي",
        "form": form,
        "generated_payload": generated_payload,
        "saved_object": saved_object,
        "saved_object_admin_url": saved_object_admin_url,
        "log_entry": log_entry,
        "logs": AIContentGenerationLog.objects.select_related("user")[:12],
        "ai_key_configured": ai_key_configured,
    }
    return render(request, "admin/ai_content_generator.html", context)


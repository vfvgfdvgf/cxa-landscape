from django.db import migrations


PRESETS = {
    "manifesto": {
        "video_url": "/videos/story-transplant.mp4",
        "poster_url": "/video-posters/story-transplant.webp",
        "media_alt": "نقل وزراعة النخيل ضمن تنفيذ اللاندسكيب",
        "overlay_opacity": 74,
    },
    "services": {
        "video_url": "/videos/story-care.mp4",
        "poster_url": "/video-posters/story-care.webp",
        "media_alt": "العناية بالحدائق والنخيل وشبكات الري",
        "overlay_opacity": 79,
    },
    "faq": {
        "video_url": "/videos/story-night.mp4",
        "poster_url": "/video-posters/story-night.webp",
        "media_alt": "مشهد لاندسكيب ونخيل بإضاءة ليلية",
        "overlay_opacity": 82,
    },
}


def apply_video_backdrops(apps, schema_editor):
    HomeSection = apps.get_model("core", "HomeSection")
    for key, preset in PRESETS.items():
        section = HomeSection.objects.filter(key=key).first()
        if not section:
            continue

        # Preserve media that the site owner already selected in the CMS.
        section.theme = "media"
        if not section.video and not section.video_url:
            section.video_url = preset["video_url"]
        if not section.poster and not section.poster_url:
            section.poster_url = preset["poster_url"]
        if not section.media_alt:
            section.media_alt = preset["media_alt"]
        if section.overlay_opacity == 62:
            section.overlay_opacity = preset["overlay_opacity"]
        section.save()


def reverse_video_backdrops(apps, schema_editor):
    HomeSection = apps.get_model("core", "HomeSection")
    for key, preset in PRESETS.items():
        section = HomeSection.objects.filter(key=key).first()
        if not section:
            continue
        section.theme = "dark"
        if section.video_url == preset["video_url"]:
            section.video_url = ""
        if section.poster_url == preset["poster_url"]:
            section.poster_url = ""
        section.save()


class Migration(migrations.Migration):
    dependencies = [("core", "0032_alter_sitesettings_homepage_meta_description_and_more")]
    operations = [migrations.RunPython(apply_video_backdrops, reverse_video_backdrops)]

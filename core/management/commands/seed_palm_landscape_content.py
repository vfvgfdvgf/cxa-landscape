from django.core.management.base import BaseCommand
from django.utils import timezone

from core.local_seo import ensure_local_service_pages
from core.models import BlogCategory, BlogPost, BlogTag, Service


SERVICES = [
    ("توريد نخيل واشنطنيا", "washingtonia-palm-supply", "نخيل واشنطنيا للمداخل والطرق والمشاريع الخارجية"),
    ("زراعة نخيل واشنطنيا", "washingtonia-palm-planting", "زراعة نخيل واشنطنيا مع تجهيز التربة والري والتثبيت"),
    ("توريد نخيل ملوكي", "royal-palm-supply", "توريد نخيل ملوكي للمشاريع السكنية والتجارية"),
    ("زراعة نخيل ملوكي", "royal-palm-planting", "تنفيذ زراعة النخيل الملوكي بتوزيع جمالي مدروس"),
    ("توريد نخيل بلدي", "local-date-palm-supply", "توريد نخيل بلدي مناسب للمزارع والاستراحات والفلل"),
    ("زراعة نخيل مثمر", "fruiting-date-palm-planting", "زراعة نخيل مثمر مع اختيار الأصناف المناسبة للموقع"),
    ("نقل نخيل كبير", "large-palm-transplanting", "نقل النخيل الكبير بطرق تقلل الإجهاد وتحافظ على الجذور"),
    ("تجهيز حفر النخيل", "palm-planting-pits", "تجهيز الحفر والتربة والأسمدة قبل زراعة النخيل"),
    ("تنسيق حدائق فلل", "villa-landscaping", "تصميم وتنفيذ حدائق الفلل بتوزيع نباتي وعملي"),
    ("تصميم لاندسكيب خارجي", "outdoor-landscape-design", "تصميم لاندسكيب خارجي يجمع الجمال وسهولة الصيانة"),
    ("تنفيذ لاندسكيب للمنازل", "home-landscape-implementation", "تنفيذ أعمال اللاندسكيب للمنازل من التخطيط حتى الزراعة"),
    ("لاندسكيب للمشاريع التجارية", "commercial-landscaping", "لاندسكيب واجهات ومداخل وممرات للمشاريع التجارية"),
    ("زراعة أشجار ظل", "shade-trees-planting", "زراعة أشجار ظل مناسبة للمناخ السعودي والمساحات الخارجية"),
    ("توريد أشجار ظل", "shade-trees-supply", "توريد أشجار ظل بأحجام مختلفة للمنازل والمشاريع"),
    ("زراعة أشجار زينة", "ornamental-trees-planting", "زراعة أشجار زينة تضيف قيمة بصرية للحديقة"),
    ("توريد أشجار زينة", "ornamental-trees-supply", "توريد أشجار زينة مختارة للمداخل والجلسات"),
    ("زراعة أشجار زيتون", "olive-trees-planting", "زراعة أشجار زيتون للحدائق والمزارع والاستراحات"),
    ("توريد أشجار زيتون", "olive-trees-supply", "توريد زيتون بأحجام مناسبة للتنسيق الخارجي"),
    ("زراعة أشجار ليمون", "lemon-trees-planting", "زراعة أشجار ليمون مع إعداد الري والتسميد"),
    ("توريد أشجار حمضيات", "citrus-trees-supply", "توريد أشجار حمضيات مثمرة للحدائق المنزلية"),
    ("زراعة عشب طبيعي", "natural-grass-installation", "تركيب وزراعة عشب طبيعي للمسطحات الخارجية"),
    ("تركيب عشب صناعي", "artificial-grass-installation", "تركيب عشب صناعي بجودة مناسبة للاستخدام اليومي"),
    ("شبكات ري حدائق", "garden-irrigation-systems", "تنفيذ شبكات ري للحدائق والنخيل والأشجار"),
    ("ري بالتنقيط للنخيل", "palm-drip-irrigation", "تصميم ري بالتنقيط يحافظ على الماء وصحة النخيل"),
    ("صيانة حدائق شهرية", "monthly-garden-maintenance", "صيانة شهرية تشمل القص والتنظيف والتسميد والمتابعة"),
    ("تقليم نخيل", "palm-pruning", "تقليم نخيل آمن يحسن الشكل ويقلل المخاطر"),
    ("تنظيف جذوع النخيل", "palm-trunk-cleaning", "تنظيف وتجميل جذوع النخيل للواجهات والحدائق"),
    ("علاج أمراض النخيل", "palm-disease-treatment", "متابعة وعلاج مشكلات النخيل الشائعة مبكرًا"),
    ("تسميد النخيل", "palm-fertilization", "برامج تسميد للنخيل حسب التربة والموسم"),
    ("تجهيز تربة الحدائق", "garden-soil-preparation", "تحسين وخلط التربة قبل الزراعة واللاندسكيب"),
    ("زراعة شجيرات سياج", "hedge-shrubs-planting", "زراعة شجيرات سياج للخصوصية وتحديد المساحات"),
    ("توريد شجيرات زينة", "ornamental-shrubs-supply", "توريد شجيرات زينة مناسبة للممرات والجلسات"),
    ("تنسيق مداخل الفلل", "villa-entrance-landscaping", "تنسيق مداخل الفلل بالنخيل والأشجار والإضاءة"),
    ("تنسيق جلسات خارجية", "outdoor-seating-landscaping", "تجهيز جلسات خارجية بنباتات وظلال وتوزيع مريح"),
    ("تصميم أحواض زراعة", "planting-beds-design", "تصميم أحواض زراعة مرتبة وسهلة الصيانة"),
    ("زراعة نباتات خارجية", "outdoor-plants-planting", "اختيار وزراعة نباتات خارجية تتحمل الحرارة"),
    ("توريد نباتات خارجية", "outdoor-plants-supply", "توريد نباتات خارجية للحدائق والأسطح والمداخل"),
    ("لاندسكيب استراحات", "resort-rest-house-landscaping", "تنفيذ لاندسكيب للاستراحات والمساحات المفتوحة"),
    ("لاندسكيب مزارع", "farm-landscaping", "تنسيق مزارع بالنخيل والأشجار ومسارات الري"),
    ("زراعة أشجار مثمرة", "fruit-trees-planting", "زراعة أشجار مثمرة مختارة حسب المساحة والموسم"),
    ("توريد أشجار مثمرة", "fruit-trees-supply", "توريد أشجار مثمرة للمنازل والاستراحات"),
    ("تركيب شبكات ري ذكية", "smart-irrigation-systems", "تركيب ري ذكي يساعد على تقليل الهدر والمتابعة"),
    ("تجديد حدائق قديمة", "garden-renovation", "إعادة ترتيب الحدائق القديمة وتحسين الزراعة والري"),
    ("تأهيل مسطحات خضراء", "green-areas-rehabilitation", "تأهيل المسطحات الخضراء للمنازل والمرافق"),
    ("توريد تربة زراعية", "agricultural-soil-supply", "توريد تربة زراعية محسنة للحدائق والنخيل"),
    ("توريد سماد عضوي", "organic-fertilizer-supply", "توريد سماد عضوي لدعم نمو الأشجار والنخيل"),
    ("مكافحة آفات الحدائق", "garden-pest-control", "مكافحة آفات الحدائق والنباتات بطرق مناسبة"),
    ("توزيع نباتات حول المسابح", "pool-landscaping", "تنسيق نباتات حول المسابح بمظهر نظيف وآمن"),
    ("لاندسكيب أسطح", "rooftop-landscaping", "تنسيق أسطح بزراعة خفيفة وري مناسب"),
    ("استشارات زراعية للمشاريع", "landscape-agricultural-consulting", "استشارات زراعية لاختيار النخيل والأشجار والري"),
]


ARTICLES = [
    ("دليل توريد النخيل المناسب للفلل والمشاريع", "palm-supply-guide-villas-projects", "توريد النخيل"),
    ("أفضل أنواع النخيل للاندسكيب في السعودية", "best-palms-for-landscaping-saudi", "أنواع النخيل"),
    ("خطوات زراعة النخيل بطريقة صحيحة", "proper-palm-planting-steps", "زراعة النخيل"),
    ("متى يكون نقل النخيل الكبير آمنًا؟", "safe-large-palm-transplanting", "نقل النخيل"),
    ("كيف تختار نخيل واجهة الفيلا؟", "choose-front-yard-palms", "نخيل الفلل"),
    ("أهمية تجهيز التربة قبل زراعة الأشجار", "soil-preparation-before-trees", "تجهيز التربة"),
    ("ري النخيل بالتنقيط: فوائد ونصائح", "palm-drip-irrigation-benefits", "ري النخيل"),
    ("أخطاء شائعة عند زراعة النخيل", "common-palm-planting-mistakes", "زراعة النخيل"),
    ("دليل تصميم لاندسكيب عملي للمنزل", "practical-home-landscape-design", "تصميم لاندسكيب"),
    ("كيف يحسن اللاندسكيب قيمة العقار؟", "landscaping-property-value", "لاندسكيب"),
    ("أفضل أشجار ظل للحدائق في السعودية", "best-shade-trees-saudi-gardens", "أشجار ظل"),
    ("أشجار زينة مناسبة للمداخل والجلسات", "ornamental-trees-entrances-seating", "أشجار زينة"),
    ("الفرق بين العشب الطبيعي والصناعي", "natural-vs-artificial-grass", "عشب الحدائق"),
    ("كيف تختار شبكة ري مناسبة للحديقة؟", "choose-garden-irrigation-system", "شبكات الري"),
    ("برنامج صيانة حدائق شهري للمنازل", "monthly-garden-maintenance-plan", "صيانة الحدائق"),
    ("تقليم النخيل: متى ولماذا؟", "palm-pruning-when-why", "تقليم النخيل"),
    ("علامات احتياج النخيل إلى تسميد", "palm-fertilization-signs", "تسميد النخيل"),
    ("أفكار تنسيق مداخل الفلل بالنخيل", "villa-entrance-palm-landscaping-ideas", "مداخل الفلل"),
    ("تنسيق جلسات خارجية بنباتات تتحمل الحرارة", "heat-tolerant-outdoor-seating-plants", "جلسات خارجية"),
    ("أفضل نباتات خارجية للمناخ الحار", "best-outdoor-plants-hot-climate", "نباتات خارجية"),
    ("لاندسكيب الاستراحات: أفكار عملية", "rest-house-landscaping-ideas", "لاندسكيب استراحات"),
    ("كيف تنسق مزرعة بالنخيل والأشجار؟", "farm-landscaping-palms-trees", "لاندسكيب مزارع"),
    ("أشجار مثمرة مناسبة للحدائق المنزلية", "fruit-trees-home-gardens", "أشجار مثمرة"),
    ("متى تحتاج الحديقة إلى تجديد كامل؟", "when-garden-needs-renovation", "تجديد الحدائق"),
    ("فوائد الري الذكي في مشاريع اللاندسكيب", "smart-irrigation-landscape-benefits", "ري ذكي"),
    ("كيف تقلل استهلاك الماء في الحديقة؟", "reduce-garden-water-use", "توفير الماء"),
    ("دليل مكافحة آفات الحدائق مبكرًا", "early-garden-pest-control-guide", "مكافحة الآفات"),
    ("تنسيق نباتات حول المسابح بدون فوضى", "pool-plants-landscaping-guide", "لاندسكيب مسابح"),
    ("لاندسكيب الأسطح: أفكار ونصائح", "rooftop-landscaping-tips", "لاندسكيب أسطح"),
    ("كيف تختار أشجارًا لا تسبب مشاكل للجدران؟", "choose-safe-trees-near-walls", "اختيار الأشجار"),
    ("توريد الأشجار للمشاريع: ما الذي يجب فحصه؟", "tree-supply-project-checklist", "توريد الأشجار"),
    ("زراعة الزيتون في الحدائق السعودية", "olive-trees-saudi-gardens", "أشجار الزيتون"),
    ("زراعة الحمضيات في المنزل: أساسيات مهمة", "home-citrus-planting-basics", "أشجار الحمضيات"),
    ("كيف تصمم أحواض زراعة جذابة؟", "attractive-planting-beds-design", "أحواض زراعة"),
    ("شجيرات السياج للخصوصية والجمال", "hedge-shrubs-privacy-beauty", "شجيرات سياج"),
    ("أهمية اختيار نباتات تتحمل الحرارة", "heat-tolerant-plants-importance", "نباتات تتحمل الحرارة"),
    ("مراحل تنفيذ مشروع لاندسكيب ناجح", "successful-landscape-project-steps", "تنفيذ لاندسكيب"),
    ("كيف تجهز موقع زراعة النخيل؟", "prepare-palm-planting-site", "موقع زراعة النخيل"),
    ("العناية بالنخيل بعد الزراعة", "palm-care-after-planting", "عناية النخيل"),
    ("اختيار مقاسات النخيل للمداخل والطرق", "palm-sizes-entrances-roads", "مقاسات النخيل"),
    ("أفكار لاندسكيب قليلة الصيانة", "low-maintenance-landscaping-ideas", "حدائق قليلة الصيانة"),
    ("كيف توزع الأشجار داخل الحديقة؟", "tree-layout-garden-design", "توزيع الأشجار"),
    ("أفضل وقت لزراعة الأشجار في السعودية", "best-time-plant-trees-saudi", "زراعة الأشجار"),
    ("مزايا السماد العضوي للحدائق والنخيل", "organic-fertilizer-gardens-palms", "سماد عضوي"),
    ("تجهيز الحدائق قبل الصيف", "prepare-gardens-before-summer", "صيانة الصيف"),
    ("مشاكل الري الزائد على النخيل والأشجار", "overwatering-palms-trees-problems", "الري الزائد"),
    ("كيف تختار شركة توريد نخيل؟", "choose-palm-supply-company", "شركة توريد نخيل"),
    ("كيف تختار شركة لاندسكيب؟", "choose-landscaping-company", "شركة لاندسكيب"),
    ("دليل سريع لتنسيق حدائق الشركات", "commercial-garden-landscaping-guide", "حدائق الشركات"),
    ("خدمات النخيل واللاندسكيب المتكاملة", "complete-palm-landscaping-services", "خدمات متكاملة"),
]


class Command(BaseCommand):
    help = "Seed palm, landscaping, trees, and irrigation services plus SEO blog articles."

    def handle(self, *args, **options):
        category, _ = BlogCategory.objects.update_or_create(
            slug="palm-landscaping-services",
            defaults={
                "name": "خدمات النخيل واللاندسكيب",
                "description": "مقالات عن توريد النخيل وزراعته واللاندسكيب والأشجار وشبكات الري.",
                "meta_title": "خدمات النخيل واللاندسكيب في السعودية",
                "meta_description": "دليل مقالات متخصص في توريد النخيل وزراعته وتنسيق الحدائق والأشجار والري.",
            },
        )
        tags = []
        for tag_name, tag_slug in [
            ("نخيل", "palms"),
            ("لاندسكيب", "landscaping"),
            ("أشجار", "trees"),
            ("ري", "irrigation"),
        ]:
            tag, _ = BlogTag.objects.update_or_create(
                slug=tag_slug,
                defaults={"name": tag_name, "meta_title": tag_name, "meta_description": tag_name},
            )
            tags.append(tag)

        created_services = updated_services = 0
        for index, (title, slug, short_title) in enumerate(SERVICES, start=1):
            description = (
                f"{title} خدمة موجهة للمنازل والفلل والاستراحات والمشاريع داخل السعودية. "
                "نبدأ بفحص الموقع واختيار المقاس أو النوع المناسب، ثم نجهز التربة ونقترح طريقة الري والعناية بعد التنفيذ. "
                "الهدف هو الحصول على نتيجة جميلة ومستقرة وسهلة الصيانة، مع مراعاة طبيعة المناخ واحتياج النخيل أو الأشجار للماء والتسميد."
            )
            service, created = Service.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "short_title": short_title,
                    "description": description,
                    "benefits": "\n".join(
                        [
                            "اختيار نوع ومقاس مناسب للموقع",
                            "تجهيز التربة والري قبل التنفيذ",
                            "تنفيذ مرتب يحافظ على الشكل العام",
                            "نصائح عناية بعد الزراعة أو التركيب",
                        ]
                    ),
                    "meta_title": f"{title} في السعودية | توريد وزراعة ولاندسكيب",
                    "meta_description": f"{title} للمنازل والمشاريع مع تجهيز التربة والري والعناية المناسبة للنخيل والأشجار.",
                    "meta_keywords": f"{title}, توريد نخيل, زراعة نخيل, لاندسكيب, أشجار, تنسيق حدائق",
                    "is_visible": True,
                    "display_order": index,
                },
            )
            created_services += int(created)
            updated_services += int(not created)

        created_posts = updated_posts = 0
        for index, (title, slug, keyword) in enumerate(ARTICLES, start=1):
            excerpt = f"دليل عملي عن {keyword} ضمن خدمات توريد النخيل وزراعته واللاندسكيب والأشجار في السعودية."
            content = f"""
<h2>{title}</h2>
<p>تحتاج خدمات {keyword} إلى تخطيط واضح قبل التنفيذ، لأن اختيار النوع المناسب وتجهيز الموقع وشبكة الري يحدد جودة النتيجة لسنوات. في أعمال توريد النخيل وزراعته واللاندسكيب، لا يكفي اختيار نبات جميل فقط؛ بل يجب مراعاة حجم المساحة، اتجاه الشمس، جودة التربة، وطريقة الصيانة المتوقعة.</p>
<h3>ما الذي نركز عليه في الخدمة؟</h3>
<p>نبدأ بمعاينة الموقع وتحديد الأنواع المناسبة من النخيل أو الأشجار أو النباتات الخارجية. بعد ذلك يتم تجهيز التربة، تحديد أماكن الزراعة، وضبط الري بما يناسب طبيعة النبات. هذا الأسلوب يقلل الهدر ويحسن ثبات الزراعة بعد التنفيذ.</p>
<h3>لماذا التخطيط مهم؟</h3>
<p>التخطيط الجيد يساعد على توزيع الأشجار والنخيل بطريقة لا تعيق الحركة ولا تؤثر على الجدران أو الممرات. كما يجعل الحديقة أسهل في الصيانة وأكثر قدرة على تحمل حرارة الصيف وتغيرات الموسم.</p>
<h3>نصيحة قبل التنفيذ</h3>
<p>اختر مزود خدمة يفهم الفرق بين التوريد، الزراعة، العناية، والري. الجمع بين هذه العناصر هو ما يصنع لاندسكيب ناجحًا، خصوصًا في المشاريع التي تعتمد على النخيل والأشجار كمظهر رئيسي.</p>
""".strip()
            post, created = BlogPost.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "excerpt": excerpt,
                    "content": content,
                    "category": category,
                    "status": "published",
                    "publish_at": timezone.now(),
                    "meta_title": f"{title} | خدمات النخيل واللاندسكيب",
                    "meta_description": excerpt,
                    "meta_keywords": f"{keyword}, توريد نخيل, زراعة نخيل, لاندسكيب, أشجار, تنسيق حدائق",
                    "is_featured": index <= 6,
                },
            )
            post.tags.set(tags)
            created_posts += int(created)
            updated_posts += int(not created)

        ensure_local_service_pages(overwrite=False)
        self.stdout.write(self.style.SUCCESS(f"created_services={created_services} updated_services={updated_services}"))
        self.stdout.write(self.style.SUCCESS(f"created_posts={created_posts} updated_posts={updated_posts}"))

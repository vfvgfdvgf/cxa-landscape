from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import PublicPageNumberPagination
from core.api.serializers import (
    ArticleCardSerializer,
    ArticleSerializer,
    CategorySerializer,
    CitySerializer,
    CityServiceCardSerializer,
    CityServiceSerializer,
    DistrictListSerializer,
    DistrictSerializer,
    PageSerializer,
    ProjectCardSerializer,
    ProjectSerializer,
    ServiceCardSerializer,
    ServiceSerializer,
    ServiceCategorySerializer,
    TagSerializer,
)
from core.api.utils import cap_repeated_media, published_blog_filter
from core.models import (
    BlogCategory,
    BlogPost,
    BlogTag,
    City,
    CityServicePage,
    District,
    Page,
    Project,
    Service,
    ServiceCategory,
)


def paginated_response(view, request, queryset, serializer_class):
    paginator = PublicPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    serializer = serializer_class(page, many=True, context={"request": request})
    return paginator.get_paginated_response(cap_repeated_media(serializer.data))


def service_queryset():
    return Service.objects.filter(is_visible=True).select_related(
        "category", "primary_city", "primary_district", "primary_district__city"
    ).prefetch_related("tags", "cities")


def service_card_queryset():
    return Service.objects.filter(is_visible=True).select_related(
        "category", "primary_city"
    )


def project_card_queryset():
    return Project.objects.filter(is_visible=True).select_related(
        "city", "district", "coverage_city", "coverage_district"
    )


def article_card_queryset():
    return BlogPost.objects.filter(published_blog_filter()).select_related(
        "category", "city", "district"
    )


def local_service_card_queryset():
    return CityServicePage.objects.filter(
        is_active=True,
        city__is_active=True,
        service__is_visible=True,
    ).select_related(
        "city", "district", "service", "service__category", "service__primary_city"
    )


def service_category_queryset():
    return (
        ServiceCategory.objects.filter(services__is_visible=True)
        .annotate(service_count=Count("services", filter=Q(services__is_visible=True), distinct=True))
        .distinct()
        .order_by("name")
    )


def project_queryset():
    return Project.objects.filter(is_visible=True).select_related(
        "city", "district", "coverage_city", "coverage_district"
    ).prefetch_related("gallery")


def article_queryset():
    return BlogPost.objects.filter(published_blog_filter()).select_related(
        "category", "city", "district"
    ).prefetch_related("tags")


def category_queryset():
    return BlogCategory.objects.filter(
        posts__status="published",
    ).filter(
        Q(posts__publish_at__lte=timezone.now()) | Q(posts__publish_at__isnull=True)
    ).distinct()


def tag_queryset():
    return BlogTag.objects.filter(
        posts__status="published",
    ).filter(
        Q(posts__publish_at__lte=timezone.now()) | Q(posts__publish_at__isnull=True)
    ).distinct()


def city_queryset():
    active_districts = District.objects.filter(is_active=True).order_by("sort_order", "name")
    return City.objects.filter(is_active=True).prefetch_related(
        Prefetch("districts", queryset=active_districts, to_attr="active_districts")
    )


def local_service_queryset():
    return CityServicePage.objects.filter(
        is_active=True,
        city__is_active=True,
        service__is_visible=True,
    ).select_related(
        "city", "district", "service", "service__category", "service__primary_city",
        "service__primary_district", "service__primary_district__city",
    ).prefetch_related("service__tags", "service__cities")


class PageListView(APIView):
    def get(self, request):
        return paginated_response(self, request, Page.objects.filter(is_visible=True), PageSerializer)


class PageDetailView(APIView):
    def get(self, request, slug):
        queryset = Page.objects.filter(is_visible=True)
        # Resolve deterministically. One OR-query can match two different rows
        # (for example a custom_url equal to another page's template_key) and
        # make get_object_or_404 raise MultipleObjectsReturned.
        page = queryset.filter(slug=slug).first()
        if page is None:
            page = queryset.filter(custom_url=slug).first()
        if page is None:
            page = queryset.filter(template_key=slug).first()
        if page is None:
            raise Http404
        return Response(cap_repeated_media(PageSerializer(page, context={"request": request}).data))


class ServiceListView(APIView):
    def get(self, request):
        queryset = service_card_queryset()
        query = request.query_params.get("q", "").strip()
        category = request.query_params.get("category", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if category:
            queryset = queryset.filter(category__slug=category)
        return paginated_response(self, request, queryset, ServiceCardSerializer)


class ServiceCategoryListView(APIView):
    def get(self, request):
        return Response(
            ServiceCategorySerializer(
                service_category_queryset(), many=True, context={"request": request}
            ).data
        )


class ServiceCategoryDetailView(APIView):
    def get(self, request, slug):
        category = get_object_or_404(service_category_queryset(), slug=slug)
        return Response(ServiceCategorySerializer(category, context={"request": request}).data)


class ServiceDetailView(APIView):
    def get(self, request, slug):
        service = get_object_or_404(service_queryset(), slug=slug)
        return Response(cap_repeated_media(ServiceSerializer(service, context={"request": request}).data))


class ProjectListView(APIView):
    def get(self, request):
        queryset = project_card_queryset()
        city = request.query_params.get("city", "").strip()
        if city:
            queryset = queryset.filter(Q(city__slug=city) | Q(coverage_city__slug=city)).distinct()
        return paginated_response(self, request, queryset, ProjectCardSerializer)


class ProjectDetailView(APIView):
    def get(self, request, slug):
        project = get_object_or_404(project_queryset(), slug=slug)
        return Response(cap_repeated_media(ProjectSerializer(project, context={"request": request}).data))


class CityListView(APIView):
    def get(self, request):
        return paginated_response(self, request, city_queryset(), CitySerializer)


class DistrictListView(APIView):
    def get(self, request):
        queryset = District.objects.filter(is_active=True, city__is_active=True).select_related("city")
        city = request.query_params.get("city", "").strip()
        query = request.query_params.get("q", "").strip()
        if city:
            queryset = queryset.filter(city__slug=city)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(city__name__icontains=query))
        queryset = queryset.order_by("city__name", "sort_order", "name")
        return paginated_response(self, request, queryset, DistrictListSerializer)


class CityDetailView(APIView):
    def get(self, request, city_slug):
        city = get_object_or_404(city_queryset(), slug=city_slug)
        context = {"request": request}
        data = CitySerializer(city, context=context).data
        data["projects"] = ProjectCardSerializer(
            project_card_queryset().filter(Q(city=city) | Q(coverage_city=city)).distinct()[:12],
            many=True, context=context
        ).data
        data["services"] = CityServiceCardSerializer(
            local_service_card_queryset().filter(city=city)[:12],
            many=True, context=context,
        ).data
        data["articles"] = ArticleCardSerializer(
            article_card_queryset().filter(city=city)[:8], many=True, context=context
        ).data
        return Response(cap_repeated_media(data))


class CityDistrictListView(APIView):
    def get(self, request, city_slug):
        city = get_object_or_404(City.objects.filter(is_active=True), slug=city_slug)
        queryset = District.objects.filter(city=city, is_active=True).select_related("city")
        return paginated_response(self, request, queryset, DistrictSerializer)


class DistrictDetailView(APIView):
    def get(self, request, city_slug, district_slug):
        projects = project_card_queryset()
        district = get_object_or_404(
            District.objects.filter(city__slug=city_slug, city__is_active=True, is_active=True)
            .select_related("city"),
            slug=district_slug,
        )
        district.public_projects = list(
            projects.filter(Q(district=district) | Q(coverage_district=district)).distinct()[:12]
        )
        context = {"request": request}
        data = DistrictSerializer(district, context=context).data
        data["services"] = CityServiceCardSerializer(
            local_service_card_queryset().filter(city=district.city).filter(
                Q(district=district) | Q(district__isnull=True)
            )[:12],
            many=True, context=context,
        ).data
        data["articles"] = ArticleCardSerializer(
            article_card_queryset().filter(Q(district=district) | Q(city=district.city))[:8],
            many=True, context=context,
        ).data
        return Response(cap_repeated_media(data))


class CityServiceDetailView(APIView):
    def get(self, request, city_slug, service_slug):
        queryset = local_service_queryset().filter(city__slug=city_slug)
        page = queryset.filter(Q(custom_slug=service_slug) | Q(service__slug=service_slug)).first()
        if not page:
            from django.http import Http404

            raise Http404("Service page not found")
        return Response(cap_repeated_media(CityServiceSerializer(page, context={"request": request}).data))


class DistrictServiceDetailView(APIView):
    def get(self, request, city_slug, district_slug, service_slug):
        district = get_object_or_404(
            District.objects.select_related("city"),
            city__slug=city_slug,
            slug=district_slug,
            city__is_active=True,
            is_active=True,
        )
        queryset = local_service_queryset().filter(
            city=district.city,
            district=district,
        )
        page = queryset.filter(Q(custom_slug=service_slug) | Q(service__slug=service_slug)).first()
        if not page:
            from django.http import Http404

            raise Http404("District service page not found")
        return Response(cap_repeated_media(CityServiceSerializer(page, context={"request": request}).data))


class ArticleListView(APIView):
    def get(self, request):
        queryset = article_card_queryset()
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(content__icontains=query))
        return paginated_response(self, request, queryset, ArticleCardSerializer)


class ArticleDetailView(APIView):
    def get(self, request, slug):
        post = get_object_or_404(article_queryset(), slug=slug)
        context = {"request": request}
        data = ArticleSerializer(post, context=context).data
        related = article_queryset().exclude(pk=post.pk)
        if post.category_id:
            related = related.filter(category_id=post.category_id)
        elif post.city_id:
            related = related.filter(city_id=post.city_id)
        else:
            related = related.none()
        data["related_articles"] = ArticleCardSerializer(related[:3], many=True, context=context).data
        return Response(cap_repeated_media(data))


class CategoryListView(APIView):
    def get(self, request):
        return Response(CategorySerializer(category_queryset(), many=True, context={"request": request}).data)


class CategoryDetailView(APIView):
    def get(self, request, slug):
        category = get_object_or_404(category_queryset(), slug=slug)
        articles = article_card_queryset().filter(category=category)
        data = CategorySerializer(category, context={"request": request}).data
        response = paginated_response(self, request, articles, ArticleCardSerializer)
        data["articles"] = response.data
        return Response(data)


class TagListView(APIView):
    def get(self, request):
        return Response(TagSerializer(tag_queryset(), many=True, context={"request": request}).data)


class TagDetailView(APIView):
    def get(self, request, slug):
        tag = get_object_or_404(tag_queryset(), slug=slug)
        articles = article_card_queryset().filter(tags=tag)
        data = TagSerializer(tag, context={"request": request}).data
        response = paginated_response(self, request, articles, ArticleCardSerializer)
        data["articles"] = response.data
        return Response(data)


class ArchiveView(APIView):
    def get(self, request):
        return Response(
            {
                "services": service_queryset().count(),
                "cities": City.objects.filter(is_active=True).count(),
                "districts": District.objects.filter(is_active=True, city__is_active=True).count(),
                "articles": article_queryset().count(),
                "projects": project_queryset().count(),
            }
        )


class ArchiveServicesView(ServiceListView):
    pass


class ArchiveCitiesView(CityListView):
    pass


class ArchiveArticlesView(ArticleListView):
    pass

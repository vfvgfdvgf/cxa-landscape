from django.urls import path

from core.api import views


app_name = "api_v1"

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("ready/", views.ReadyView.as_view(), name="ready"),
    path("site/", views.SiteView.as_view(), name="site"),
    path("navigation/", views.NavigationView.as_view(), name="navigation"),
    path("home/", views.HomeView.as_view(), name="home"),
    path("pages/", views.PageListView.as_view(), name="pages"),
    path("pages/<slug:slug>/", views.PageDetailView.as_view(), name="page-detail"),
    path("services/", views.ServiceListView.as_view(), name="services"),
    path("service-categories/", views.ServiceCategoryListView.as_view(), name="service-categories"),
    path("service-categories/<slug:slug>/", views.ServiceCategoryDetailView.as_view(), name="service-category-detail"),
    path("services/<slug:slug>/", views.ServiceDetailView.as_view(), name="service-detail"),
    path("projects/", views.ProjectListView.as_view(), name="projects"),
    path("projects/<slug:slug>/", views.ProjectDetailView.as_view(), name="project-detail"),
    path("cities/", views.CityListView.as_view(), name="cities"),
    path("districts/", views.DistrictListView.as_view(), name="district-index"),
    path("cities/<slug:city_slug>/", views.CityDetailView.as_view(), name="city-detail"),
    path("cities/<slug:city_slug>/districts/", views.CityDistrictListView.as_view(), name="districts"),
    path("cities/<slug:city_slug>/districts/<str:district_slug>/", views.DistrictDetailView.as_view(), name="district-detail"),
    path("cities/<slug:city_slug>/districts/<str:district_slug>/services/<slug:service_slug>/", views.DistrictServiceDetailView.as_view(), name="district-service-detail"),
    path("cities/<slug:city_slug>/services/<slug:service_slug>/", views.CityServiceDetailView.as_view(), name="city-service-detail"),
    path("blog/", views.ArticleListView.as_view(), name="articles"),
    path("blog/categories/", views.CategoryListView.as_view(), name="categories"),
    path("blog/categories/<str:slug>/", views.CategoryDetailView.as_view(), name="category-detail"),
    path("blog/tags/", views.TagListView.as_view(), name="tags"),
    path("blog/tags/<str:slug>/", views.TagDetailView.as_view(), name="tag-detail"),
    path("blog/<slug:slug>/", views.ArticleDetailView.as_view(), name="article-detail"),
    path("testimonials/", views.TestimonialListView.as_view(), name="testimonials"),
    path("redirects/", views.RedirectListView.as_view(), name="redirects"),
    path("public-urls/", views.PublicUrlsView.as_view(), name="public-urls"),
    path("tools/", views.ToolContentView.as_view(), name="tools"),
    path("archive/", views.ArchiveView.as_view(), name="archive"),
    path("archive/services/", views.ArchiveServicesView.as_view(), name="archive-services"),
    path("archive/cities/", views.ArchiveCitiesView.as_view(), name="archive-cities"),
    path("archive/articles/", views.ArchiveArticlesView.as_view(), name="archive-articles"),
    path("contact/", views.ContactSubmissionView.as_view(), name="contact"),
    path("quote-request/", views.QuoteSubmissionView.as_view(), name="quote-request"),
    path("leads/", views.LeadSubmissionView.as_view(), name="leads"),
]

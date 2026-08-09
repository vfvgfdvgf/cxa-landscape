import Link from "next/link";

export function EmptyState({ message = "لا يوجد محتوى منشور في هذا القسم حاليًا." }: { message?: string }) {
  return <div className="empty-state" role="status">{message}</div>;
}

export function Pagination({ current, count, pageSize, href }: { current: number; count: number; pageSize: number; href: string }) {
  const pages = Math.ceil(count / pageSize);
  if (pages <= 1) return null;
  const pageHref = (page: number) => `${href}${href.includes("?") ? "&" : "?"}page=${page}`;
  return (
    <nav className="pagination" aria-label="صفحات النتائج">
      {current > 1 ? <Link href={pageHref(current - 1)}>السابق</Link> : <span aria-disabled="true">السابق</span>}
      <span>صفحة {current} من {pages}</span>
      {current < pages ? <Link href={pageHref(current + 1)}>التالي</Link> : <span aria-disabled="true">التالي</span>}
    </nav>
  );
}

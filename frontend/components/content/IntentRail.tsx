import Link from "next/link";

import type { MarketIntent } from "@/lib/market-intents";

export function IntentRail({
  eyebrow = "ما يبحث عنه العملاء",
  title,
  description,
  items,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  items: MarketIntent[];
}) {
  return (
    <section className="intent-rail" aria-labelledby="intent-rail-title">
      <div className="intent-rail__intro">
        <p className="eyebrow">{eyebrow}</p>
        <h2 id="intent-rail-title">{title}</h2>
        <p>{description}</p>
      </div>
      <div className="intent-rail__grid">
        {items.map((item, index) => (
          <Link className="intent-chip" href={item.href} key={item.label}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div><strong>{item.label}</strong><small>{item.note}</small></div>
            <b aria-hidden="true">↗</b>
          </Link>
        ))}
      </div>
    </section>
  );
}

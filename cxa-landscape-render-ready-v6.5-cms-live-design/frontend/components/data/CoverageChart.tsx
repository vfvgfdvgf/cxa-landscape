"use client";

import { useEffect, useRef } from "react";

interface CoveragePoint {
  name: string;
  count: number;
}

export function CoverageChart({ data }: { data: CoveragePoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let chart: { destroy: () => void } | undefined;
    let cancelled = false;

    void import("highcharts").then(({ default: Highcharts }) => {
      if (cancelled || !containerRef.current) return;
      chart = Highcharts.chart(containerRef.current, {
        chart: {
          type: "column",
          backgroundColor: "transparent",
          height: 410,
          spacing: [24, 0, 24, 0],
          style: { fontFamily: "var(--font-ui)" },
        },
        title: { text: undefined },
        credits: { enabled: false },
        accessibility: { enabled: false },
        legend: { enabled: false },
        tooltip: {
          borderWidth: 0,
          borderRadius: 0,
          backgroundColor: "#0c0f0d",
          style: { color: "#f2efe7", fontSize: "13px" },
          pointFormat: "<b>{point.y}</b> حي ضمن التغطية",
          useHTML: true,
        },
        xAxis: {
          categories: data.map((item) => item.name),
          lineColor: "rgba(12,15,13,.22)",
          tickLength: 0,
          labels: { style: { color: "#343a35", fontSize: "12px" } },
        },
        yAxis: {
          min: 0,
          title: { text: undefined },
          gridLineColor: "rgba(12,15,13,.10)",
          labels: { style: { color: "#6a706b", fontSize: "11px" } },
        },
        plotOptions: {
          column: {
            borderWidth: 0,
            borderRadius: 0,
            color: "#244c3a",
            maxPointWidth: 54,
            pointPadding: 0.12,
            groupPadding: 0.08,
          },
          series: {
            animation: { duration: 900 },
            states: { hover: { color: "#b99a61" } },
            dataLabels: {
              enabled: true,
              style: { color: "#0c0f0d", fontSize: "12px", fontWeight: "700", textOutline: "none" },
            },
          },
        },
        series: [{ type: "column", name: "الأحياء", data: data.map((item) => item.count) }],
      });
    });

    return () => {
      cancelled = true;
      chart?.destroy();
    };
  }, [data]);

  return <div ref={containerRef} className="coverage-chart" role="img" aria-label="مخطط يوضح عدد الأحياء المشمولة في مدن التغطية" />;
}

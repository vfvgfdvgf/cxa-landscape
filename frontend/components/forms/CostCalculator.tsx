"use client";

import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";

import type { CalculatorTool } from "@/types";

const formatter = new Intl.NumberFormat("ar-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 });

export function CostCalculator({ calculator }: { calculator: CalculatorTool }) {
  const [quantity, setQuantity] = useState(1);
  const estimate = useMemo(() => ({ min: quantity * calculator.min_rate, max: quantity * calculator.max_rate }), [calculator, quantity]);
  return (
    <div className="calculator">
      <div>
        <p className="eyebrow">تقدير أولي</p>
        <h2>{calculator.service}</h2>
        <p>{calculator.description}</p>
        <div className="form-field"><label htmlFor="calculator-quantity">الكمية ({calculator.unit})</label><input id="calculator-quantity" type="number" min={1} max={100000} value={quantity} onChange={(event: ChangeEvent<HTMLInputElement>) => setQuantity(Math.max(1, Number(event.target.value) || 1))} /></div>
        <p><small>هذا نطاق تقريبي وليس عرض سعر نهائيًا؛ تختلف التكلفة بعد المعاينة والمواصفات.</small></p>
      </div>
      <div className="calculator__result"><span>النطاق التقديري</span><strong>{formatter.format(estimate.min)}</strong><span>إلى {formatter.format(estimate.max)}</span></div>
    </div>
  );
}

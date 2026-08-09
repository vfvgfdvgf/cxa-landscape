export function whatsappUrl(number = ""): string {
  const digits = number.replace(/\D/g, "").replace(/^0/, "966");
  return digits ? `https://wa.me/${digits}` : "/contact/";
}

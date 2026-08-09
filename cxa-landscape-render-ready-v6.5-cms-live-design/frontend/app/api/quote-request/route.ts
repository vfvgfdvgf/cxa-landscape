import { proxySubmission } from "@/lib/submissions";

export async function POST(request: Request) {
  return proxySubmission(request, "quote-request/");
}

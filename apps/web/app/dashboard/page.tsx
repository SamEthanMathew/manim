import { redirect } from "next/navigation";

// Dashboard is folded into the homepage's Recent Jobs section now.
export default function DashboardPage() {
  redirect("/");
}
